"""Free-chat WebSocket (`/ws/chat`) + AI debug panel REST endpoint.

Independent WS from `/ws/analysis` (see phase-5-execution-plan.md §0.1):
`FreeChatSession` has a different lifecycle (one instance per *completed*
`AnalysisRecord`, surviving across the analysis WS connection closing) than
`AnalysisRunner` (one-shot submit/result). `state.chat_session` is created in
`analysis.py` right after a record is produced, mirroring
`main_window.py::_on_record_ready_impl`.
"""

from __future__ import annotations

import asyncio
import json
import logging

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect

from pa_agent.ai.prompt_assembler import stage1_prompt_txt_files, stage2_prompt_txt_files
from pa_agent.util.mask_secret import mask_secret
from pa_agent.webui.deps import AppState
from pa_agent.webui.schemas.chat import (
    ChatDebugContextRequest,
    ChatDebugContextResponse,
    ChatDebugTurn,
    PromptFilesInfo,
)

logger = logging.getLogger("pa_agent.webui")

ws_router = APIRouter()
router = APIRouter()


@ws_router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.pa_state
    run_task: asyncio.Task | None = None

    try:
        while True:
            message = await websocket.receive_json()
            mtype = message.get("type")

            if mtype == "cancel":
                state.chat_runner.cancel()
                continue

            if mtype != "send":
                continue

            if state.chat_session is None:
                await websocket.send_json(
                    {"type": "chat_error", "message": "尚无可继续追问的分析结果，请先完成一次分析", "cancelled": False}
                )
                continue

            text = str(message.get("text", "")).strip()
            if not text:
                continue

            if run_task is not None and not run_task.done():
                await websocket.send_json({"type": "chat_error", "message": "追问进行中", "cancelled": False})
                continue

            # Spawned as a background task (not awaited inline) so the receive
            # loop stays free to read a "cancel" message while the send is in
            # flight -- mirrors ws_analysis's asyncio.create_task(_run(...)).
            run_task = asyncio.create_task(state.chat_runner.send(websocket, state.chat_session, text))
    except WebSocketDisconnect:
        state.chat_runner.cancel()
    finally:
        if run_task is not None and not run_task.done():
            run_task.cancel()


def _mask(text: str, api_key: str) -> str:
    if not api_key or not text:
        return text
    return text.replace(api_key, mask_secret(api_key))


def _build_debug_turns(record, api_key: str) -> list[ChatDebugTurn]:
    """Mirrors `main_window.py::_on_record_ready_impl`'s debug.add_turn() calls
    for Stage1 / Stage2 / exception -- follow-up chat turns are never added to
    the desktop debug tab either (see phase-5-execution-plan.md §4)."""
    turns: list[ChatDebugTurn] = []
    exc_info = record.exception
    exc_json = json.dumps(exc_info, ensure_ascii=False, indent=2) if exc_info else ""

    s1_msgs = record.stage1_messages or []
    s1_system = next((m.get("content", "") for m in s1_msgs if m.get("role") == "system"), "")
    s1_user = next((m.get("content", "") for m in s1_msgs if m.get("role") == "user"), "")
    s1_raw = record.stage1_response or {}
    s1_diag = record.stage1_diagnosis
    if exc_info and exc_info.get("stage") == "stage1":
        s1_validation = exc_json
    elif s1_diag:
        s1_validation = json.dumps(s1_diag, ensure_ascii=False, indent=2)
    else:
        s1_validation = "（验证失败或无数据）"
    turns.append(
        ChatDebugTurn(
            label="Stage1 诊断",
            system_prompt=_mask(s1_system, api_key),
            user_prompt=_mask(s1_user, api_key),
            raw_response=s1_raw,
            validation_info=_mask(s1_validation, api_key),
        )
    )

    s2_msgs = record.stage2_messages or []
    s2_system = next((m.get("content", "") for m in s2_msgs if m.get("role") == "system"), "")
    s2_user = next((m.get("content", "") for m in reversed(s2_msgs) if m.get("role") == "user"), "")
    s2_raw = record.stage2_response or {}
    s2_decision = record.stage2_decision
    if exc_info and exc_info.get("stage") == "stage2":
        s2_validation = exc_json
    elif s2_decision:
        s2_validation = json.dumps(s2_decision, ensure_ascii=False, indent=2)
    else:
        s2_validation = "（验证失败或无数据）"
    turns.append(
        ChatDebugTurn(
            label="Stage2 决策",
            system_prompt=_mask(s2_system, api_key),
            user_prompt=_mask(s2_user, api_key),
            raw_response=s2_raw,
            validation_info=_mask(s2_validation, api_key),
        )
    )

    if exc_info:
        turns.append(
            ChatDebugTurn(
                label="⚠ 异常",
                system_prompt="",
                user_prompt="",
                raw_response={},
                validation_info=_mask(exc_json, api_key),
            )
        )

    return turns


def _build_prompt_files(record) -> PromptFilesInfo:
    """Mirrors `main_window.py::_on_record_ready_impl`'s `pf.set_latest_run()` call."""
    strategy_files = record.strategy_files_used or []
    experience = record.experience_loaded or []
    stage1_files = stage1_prompt_txt_files()
    stage2_files = stage2_prompt_txt_files(strategy_files)
    return PromptFilesInfo(
        stage1_files=stage1_files,
        stage2_files=stage2_files,
        stage1_builtin=bool(stage1_files),
        stage2_builtin=bool(stage2_files),
        experience_count=len(experience),
    )


@router.post("/chat/debug-context")
def get_chat_debug_context(body: ChatDebugContextRequest, request: Request) -> ChatDebugContextResponse:
    """Formats the debug panel turns + prompt files panel data for a completed
    `AnalysisRecord` (already delivered to the client via the `/ws/analysis`
    "record" message body). API-key masking happens here, server-side, since
    the frontend never has the plaintext key."""
    record = body.record
    state: AppState = request.app.state.pa_state
    ctx = state.ctx
    api_key = ""
    if ctx is not None and getattr(ctx, "settings", None) is not None:
        api_key = getattr(ctx.settings.provider, "api_key", "") or ""
    return ChatDebugContextResponse(
        turns=_build_debug_turns(record, api_key),
        prompt_files=_build_prompt_files(record),
    )
