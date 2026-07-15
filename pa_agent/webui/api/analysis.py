"""AI analysis WebSocket endpoint (full / incremental submission + cancel)."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pa_agent.webui.deps import AppState
from pa_agent.webui.services.chat_runner import build_chat_session
from pa_agent.webui.services.order_alert import maybe_alert_order_opportunity

logger = logging.getLogger("pa_agent.webui")

ws_router = APIRouter()


def _resolve_demo_record_path(record_id: str):
    """Resolve *record_id* (a bare filename from GET /api/demo/records) to a
    path inside RECORDS_PENDING_DIR, or None if it doesn't exist / escapes
    the directory (e.g. via `../`)."""
    from pa_agent.config.paths import RECORDS_PENDING_DIR

    base = RECORDS_PENDING_DIR.resolve()
    candidate = (base / record_id).resolve()
    try:
        candidate.relative_to(base)
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


@ws_router.websocket("/ws/analysis")
async def ws_analysis(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.pa_state
    run_task: asyncio.Task | None = None
    active_mode: str | None = None

    async def _run(frame, previous_record, incremental_new_bar_count) -> None:
        record = await state.analysis_runner.run(
            websocket,
            frame,
            previous_record=previous_record,
            incremental_new_bar_count=incremental_new_bar_count,
        )
        if record is not None:
            state.last_analysis_record = record
            # Phase 5: (re)build the free-chat session bound to this record,
            # mirroring main_window.py::_on_record_ready_impl's "Create
            # FreeChatSession and wire to stream panel" block.
            state.chat_session = build_chat_session(state, record)
            await maybe_alert_order_opportunity(websocket, state, record)

    async def _run_demo(demo_record_id: str) -> None:
        from pa_agent.demo.record_loader import try_load_analysis_record

        path = _resolve_demo_record_path(demo_record_id)
        if path is None:
            await websocket.send_json({"type": "error", "message": "演示记录不存在"})
            return
        record = try_load_analysis_record(path)
        if record is None:
            await websocket.send_json({"type": "error", "message": "演示记录无法读取"})
            return

        replayed = await state.demo_runner.run(websocket, record)
        if replayed is not None:
            state.last_analysis_record = replayed
            state.chat_session = build_chat_session(state, replayed)
            await maybe_alert_order_opportunity(websocket, state, replayed)

    try:
        while True:
            message = await websocket.receive_json()
            mtype = message.get("type")

            if mtype == "cancel":
                if active_mode == "demo":
                    state.demo_runner.cancel()
                else:
                    state.analysis_runner.cancel()
                continue

            if mtype != "submit":
                continue

            if run_task is not None and not run_task.done():
                await websocket.send_json({"type": "error", "message": "分析进行中"})
                continue

            mode = message.get("mode", "full")

            if mode == "demo":
                demo_record_id = message.get("demo_record_id")
                if not demo_record_id:
                    await websocket.send_json({"type": "error", "message": "缺少 demo_record_id"})
                    continue
                active_mode = "demo"
                run_task = asyncio.create_task(_run_demo(demo_record_id))
                continue

            active_mode = "analysis"
            frame = state.active_frame()
            if frame is None:
                await websocket.send_json({"type": "error", "message": "暂无K线数据，请先获取数据"})
                continue

            previous_record = state.last_analysis_record if mode == "incremental" else None
            incremental_new_bar_count = (
                message.get("incremental_new_bar_count") if mode == "incremental" else None
            )
            run_task = asyncio.create_task(_run(frame, previous_record, incremental_new_bar_count))
    except WebSocketDisconnect:
        state.analysis_runner.cancel()
        state.demo_runner.cancel()
    finally:
        if run_task is not None and not run_task.done():
            run_task.cancel()
