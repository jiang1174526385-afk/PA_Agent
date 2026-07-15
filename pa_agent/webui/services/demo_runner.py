"""Asyncio equivalent of `pa_agent/demo/replayer.py::DemoReplayer`.

The desktop `DemoReplayer` is a `QTimer`-driven schedule that emits the same
signal set as `_AnalysisWorker` (`reasoning_token`/`content_token`/
`record_ready`/`status_update`/`finished`) to replay an already-saved
`AnalysisRecord` without a real API call. Per phase-6-execution-plan.md §0.1
(confirmed with the user), the Web equivalent reuses `/ws/analysis` -- the
step schedule below is ported from `DemoReplayer._build_steps` verbatim
(same `_CHAR_MS`/`_STAGE_GAP_MS` pacing, same step ordering) but each step is
a *wire message* in `/ws/analysis`'s existing vocabulary
(`stage1_reasoning`/`stage2_content`/`stage_prompt`/`stage2_files`/`record`/
`event`) instead of a Qt signal, plus one Web-only addition: a terminal
`demo_finished` message (there is no desktop equivalent to notify -- the
desktop UI reacts to the `replay_finished` signal directly).
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from pa_agent.ai.response_extract import content_from_response, reasoning_from_response
from pa_agent.util.threading import CancelToken

if TYPE_CHECKING:
    from fastapi import WebSocket

    from pa_agent.records.schema import AnalysisRecord

logger = logging.getLogger("pa_agent.webui")

# Same pacing constants as pa_agent/demo/replayer.py.
_CHAR_MS = 16
_STAGE_GAP_MS = 450


def _prompt_parts(messages: list[dict] | None, *, last_user: bool = False) -> tuple[str, str]:
    msgs = messages or []
    system = next((m.get("content", "") for m in msgs if m.get("role") == "system"), "")
    user_messages = reversed(msgs) if last_user else msgs
    user = next((m.get("content", "") for m in user_messages if m.get("role") == "user"), "")
    return str(system), str(user)


def build_demo_steps(record: "AnalysisRecord") -> list[tuple[int, dict[str, Any]]]:
    """Port of `DemoReplayer._build_steps` -- same schedule, wire-message shaped."""
    r = record
    steps: list[tuple[int, dict[str, Any]]] = []

    s1_sys, s1_user = _prompt_parts(r.stage1_messages)
    s2_sys, s2_user = _prompt_parts(r.stage2_messages, last_user=True)
    s1_reason = reasoning_from_response(r.stage1_response)
    s2_reason = reasoning_from_response(r.stage2_response)
    s2_content = content_from_response(r.stage2_response)
    strategy = list(r.strategy_files_used or [])

    def add(delay: int, message: dict[str, Any]) -> None:
        steps.append((delay, message))

    add(_STAGE_GAP_MS, {"type": "event", "event": "DemoStage1Started", "message": "阶段一分析中…"})
    add(80, {"type": "stage_prompt", "stage": "stage1", "system": s1_sys, "user": s1_user})
    for ch in s1_reason:
        add(_CHAR_MS, {"type": "stage1_reasoning", "chunk": ch})
    add(_STAGE_GAP_MS, {"type": "event", "event": "DemoStage1Done", "message": "阶段一完成"})

    if strategy or r.stage2_decision:
        add(200, {"type": "stage2_files", "files": strategy})
        add(_STAGE_GAP_MS, {"type": "event", "event": "DemoStage2Started", "message": "阶段二分析中…"})
        add(80, {"type": "stage_prompt", "stage": "stage2", "system": s2_sys, "user": s2_user})
        for ch in s2_reason:
            add(_CHAR_MS, {"type": "stage2_reasoning", "chunk": ch})
        if not s2_reason and s2_content:
            for ch in s2_content:
                add(_CHAR_MS, {"type": "stage2_content", "chunk": ch})
        add(_STAGE_GAP_MS, {"type": "event", "event": "DemoStage2Done", "message": "阶段二完成"})

    # Match real worker: stream ends, then record persisted, then record → finished.
    add(300, {"type": "event", "event": "DemoRecordSaved", "message": "记录已保存"})
    add(120, {"type": "record", "record": r.model_dump()})
    add(200, {"type": "demo_finished"})
    return steps


class DemoRunner:
    """Single-flight asyncio replay, mirroring `AnalysisRunner`'s busy-gate contract."""

    def __init__(self) -> None:
        self._busy = False
        self._cancel_token: CancelToken | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def cancel(self) -> None:
        if self._cancel_token is not None:
            self._cancel_token.set()

    async def run(self, ws: "WebSocket", record: "AnalysisRecord") -> "AnalysisRecord | None":
        if self._busy:
            await ws.send_json({"type": "error", "message": "分析进行中"})
            return None

        self._busy = True
        cancel_token = CancelToken()
        self._cancel_token = cancel_token
        try:
            for delay_ms, message in build_demo_steps(record):
                if cancel_token.is_set():
                    await ws.send_json(
                        {"type": "event", "event": "DemoCancelled", "message": "演示已取消"}
                    )
                    return None
                await asyncio.sleep(delay_ms / 1000)
                await ws.send_json(message)
        except Exception as exc:  # noqa: BLE001
            logger.exception("DemoRunner: replay failed")
            await ws.send_json({"type": "error", "message": str(exc)})
            return None
        finally:
            self._busy = False
            self._cancel_token = None

        return record
