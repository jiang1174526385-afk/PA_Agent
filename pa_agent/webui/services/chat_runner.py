"""Asyncio equivalent of the desktop `_ChatWorker` (QThread) that drives
`FreeChatSession.send()` -- see `pa_agent/gui/conversation_widget.py` /
`pa_agent/gui/ai_stream_window.py`.

Single-flight, same pattern as `pa_agent.webui.services.analysis_runner.AnalysisRunner`:
runs the blocking `FreeChatSession.send()` on a worker thread via
`asyncio.to_thread` and relays its streaming callbacks back onto the event
loop as WebSocket JSON messages.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from pa_agent.ai.deepseek_client import CancelledError
from pa_agent.util.threading import CancelToken

if TYPE_CHECKING:
    from fastapi import WebSocket

    from pa_agent.orchestrator.free_chat import FreeChatSession
    from pa_agent.records.schema import AnalysisRecord
    from pa_agent.webui.deps import AppState

logger = logging.getLogger("pa_agent.webui")


def build_chat_session(state: "AppState", record: "AnalysisRecord") -> "FreeChatSession | None":
    """Build a fresh `FreeChatSession` bound to *record*, mirroring
    `main_window.py::_on_record_ready_impl`'s "Create FreeChatSession and wire
    to stream panel" block. Returns None if any required singleton is missing
    (mirrors the desktop `if all(x is not None ...)` guard).
    """
    ctx = state.ctx
    if ctx is None:
        return None
    client = getattr(ctx, "client", None)
    assembler = getattr(ctx, "assembler", None)
    pending_writer = getattr(ctx, "pending_writer", None)
    ledger = getattr(ctx, "ledger", None)
    settings = getattr(ctx, "settings", None)
    if any(x is None for x in [client, assembler, pending_writer, ledger]):
        return None

    from pa_agent.ai.prompt_assembler import PromptAssembler
    from pa_agent.orchestrator.free_chat import FreeChatSession

    def _kline_snapshot_fn() -> str:
        frame = state.active_frame()
        if frame is None:
            return ""
        return PromptAssembler._render_kline_table(frame)

    try:
        return FreeChatSession(
            base_record=record,
            client=client,
            assembler=assembler,
            pending_writer=pending_writer,
            ledger=ledger,
            settings=settings,
            kline_snapshot_fn=_kline_snapshot_fn,
        )
    except Exception:  # noqa: BLE001
        logger.warning("build_chat_session: failed to construct FreeChatSession", exc_info=True)
        return None


class ChatRunner:
    def __init__(self) -> None:
        self._busy = False
        self._cancel_token: CancelToken | None = None

    @property
    def busy(self) -> bool:
        return self._busy

    def cancel(self) -> None:
        if self._cancel_token is not None:
            self._cancel_token.set()

    async def send(
        self,
        ws: "WebSocket",
        session: "FreeChatSession",
        text: str,
    ) -> None:
        if self._busy:
            await ws.send_json({"type": "chat_error", "message": "追问进行中"})
            return

        self._busy = True
        cancel_token = CancelToken()
        self._cancel_token = cancel_token
        loop = asyncio.get_running_loop()

        def send_json(message: dict[str, Any]) -> None:
            async def _send() -> None:
                try:
                    await ws.send_json(message)
                except Exception:
                    pass

            asyncio.run_coroutine_threadsafe(_send(), loop)

        def on_reasoning_token(chunk: str) -> None:
            send_json({"type": "chat_reasoning", "chunk": chunk})

        def on_content_token(chunk: str) -> None:
            send_json({"type": "chat_content", "chunk": chunk})

        try:
            reply = await asyncio.to_thread(
                session.send,
                text,
                cancel_token,
                on_reasoning_token=on_reasoning_token,
                on_content_token=on_content_token,
            )
        except CancelledError:
            await ws.send_json({"type": "chat_error", "message": "已取消", "cancelled": True})
            self._busy = False
            self._cancel_token = None
            return
        except Exception as exc:  # noqa: BLE001
            logger.exception("ChatRunner: FreeChatSession.send raised")
            await ws.send_json({"type": "chat_error", "message": str(exc), "cancelled": False})
            self._busy = False
            self._cancel_token = None
            return

        self._busy = False
        self._cancel_token = None

        usage = reply.usage
        cache_hit_rate_pct = round(usage.cache_hit_rate * 100, 1) if usage else 0.0
        message: dict[str, Any] = {
            "type": "chat_done",
            "content": reply.content,
            "reasoning": reply.reasoning_content or "",
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "cached_prompt_tokens": usage.cached_prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
                "cache_hit_rate_pct": cache_hit_rate_pct,
            },
        }

        ledger = getattr(session, "_ledger", None)
        if ledger is not None and hasattr(ledger, "breakdown"):
            breakdown = ledger.breakdown()
            if breakdown:
                message["token_usage"] = breakdown

        await ws.send_json(message)
