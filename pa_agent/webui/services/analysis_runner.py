"""Asyncio equivalent of `pa_agent/gui/main_window.py::_AnalysisWorker`.

Runs `TwoStageOrchestrator.submit()` on a worker thread (it is fully
synchronous/blocking) and relays its callbacks back onto the event loop as
WebSocket JSON messages. Single-flight: a second `run()` call while one is in
progress is rejected, mirroring the desktop app's one-worker-at-a-time model.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from pa_agent.util.threading import CancelToken, OrchestratorEvent
from pa_agent.webui.services.trade_metrics_view import build_trade_metrics

if TYPE_CHECKING:
    from fastapi import WebSocket

    from pa_agent.data.base import KlineFrame
    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
    from pa_agent.records.schema import AnalysisRecord

logger = logging.getLogger("pa_agent.webui")

# Copied from pa_agent/gui/main_window.py::_AnalysisWorker._EVENT_LABELS.
# OrchestratorEvent.InsufficientData has no desktop-side label either (same gap
# as upstream) -- falls back to str(event).
_EVENT_LABELS = {
    OrchestratorEvent.Stage1Started: "阶段一分析中…",
    OrchestratorEvent.Stage1Retry: "阶段一重试",
    OrchestratorEvent.Stage1Done: "阶段一完成",
    OrchestratorEvent.Stage1Failed: "阶段一失败",
    OrchestratorEvent.Stage2Started: "阶段二分析中…",
    OrchestratorEvent.Stage2Retry: "阶段二重试",
    OrchestratorEvent.Stage2Done: "阶段二完成",
    OrchestratorEvent.Stage2Failed: "阶段二失败",
    OrchestratorEvent.RecordSaved: "记录已保存",
    OrchestratorEvent.Cancelled: "已取消",
}


class AnalysisRunner:
    def __init__(self, orchestrator: TwoStageOrchestrator) -> None:
        self._orchestrator = orchestrator
        self._busy = False
        self._cancel_token: CancelToken | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def cancel(self) -> None:
        if self._cancel_token is not None:
            self._cancel_token.set()

    async def run(
        self,
        ws: WebSocket,
        frame: KlineFrame,
        *,
        previous_record: AnalysisRecord | None = None,
        incremental_new_bar_count: int | None = None,
    ) -> AnalysisRecord | None:
        if self._busy:
            await ws.send_json({"type": "error", "message": "分析进行中"})
            return None

        self._busy = True
        cancel_token = CancelToken()
        self._cancel_token = cancel_token
        loop = asyncio.get_running_loop()

        def send(message: dict[str, Any]) -> None:
            async def _send() -> None:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

            asyncio.run_coroutine_threadsafe(_send(), loop)

        def on_event(event: OrchestratorEvent) -> None:
            send(
                {
                    "type": "event",
                    "event": event.name,
                    "message": _EVENT_LABELS.get(event, str(event)),
                }
            )

        def on_stage1_reasoning(chunk: str) -> None:
            send({"type": "stage1_reasoning", "chunk": chunk})

        def on_stage1_content(chunk: str) -> None:
            send({"type": "stage1_content", "chunk": chunk})

        def on_stage2_reasoning(chunk: str) -> None:
            send({"type": "stage2_reasoning", "chunk": chunk})

        def on_stage2_content(chunk: str) -> None:
            send({"type": "stage2_content", "chunk": chunk})

        def on_stage_prompt(stage: str, system: str, user: str) -> None:
            send({"type": "stage_prompt", "stage": stage, "system": system, "user": user})

        def on_stage2_files(files: list[str]) -> None:
            send({"type": "stage2_files", "files": files})

        try:
            record = await asyncio.to_thread(
                self._orchestrator.submit,
                frame,
                cancel_token,
                on_event,
                on_stage1_reasoning=on_stage1_reasoning,
                on_stage1_content=on_stage1_content,
                on_stage2_reasoning=on_stage2_reasoning,
                on_stage2_content=on_stage2_content,
                on_stage_prompt=on_stage_prompt,
                on_stage2_files=on_stage2_files,
                previous_record=previous_record,
                incremental_new_bar_count=incremental_new_bar_count,
            )
        except Exception as exc:
            logger.exception("AnalysisRunner: orchestrator.submit raised")
            await ws.send_json({"type": "error", "message": str(exc)})
            return None
        finally:
            self._busy = False
            self._cancel_token = None

        await ws.send_json(
            {
                "type": "record",
                "record": record.model_dump(),
                "trade_metrics": build_trade_metrics(record),
            }
        )
        return record
