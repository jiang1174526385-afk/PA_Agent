"""AI analysis WebSocket endpoint (full / incremental submission + cancel)."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pa_agent.webui.deps import AppState
from pa_agent.webui.services.chat_runner import build_chat_session

logger = logging.getLogger("pa_agent.webui")

ws_router = APIRouter()


@ws_router.websocket("/ws/analysis")
async def ws_analysis(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.pa_state
    run_task: asyncio.Task | None = None

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

    try:
        while True:
            message = await websocket.receive_json()
            mtype = message.get("type")

            if mtype == "cancel":
                state.analysis_runner.cancel()
                continue

            if mtype != "submit":
                continue

            if run_task is not None and not run_task.done():
                await websocket.send_json({"type": "error", "message": "分析进行中"})
                continue

            frame = state.active_frame()
            if frame is None:
                await websocket.send_json({"type": "error", "message": "暂无K线数据，请先获取数据"})
                continue

            mode = message.get("mode", "full")
            previous_record = state.last_analysis_record if mode == "incremental" else None
            incremental_new_bar_count = (
                message.get("incremental_new_bar_count") if mode == "incremental" else None
            )
            run_task = asyncio.create_task(_run(frame, previous_record, incremental_new_bar_count))
    except WebSocketDisconnect:
        state.analysis_runner.cancel()
    finally:
        if run_task is not None and not run_task.done():
            run_task.cancel()
