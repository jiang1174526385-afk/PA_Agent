from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.ai.deepseek_client import AIReply, AIUsage, CancelledError
from pa_agent.webui.api import chat as chat_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner
from pa_agent.webui.services.chat_runner import ChatRunner


class FakeLedger:
    def __init__(self):
        self.added: list[AIUsage] = []

    def add(self, usage: AIUsage) -> None:
        self.added.append(usage)

    def breakdown(self) -> dict:
        return {
            "total_input": 100,
            "total_cached_input": 20,
            "total_output": 50,
            "context_used": 150,
            "context_window": 1_000_000,
            "context_pct": 0.02,
        }


class FakeChatSession:
    """Mirrors FreeChatSession.send()'s callback/return contract without any
    real DeepSeekClient/PromptAssembler wiring."""

    def __init__(self, *, delay_s: float = 0.0, raise_cancelled: bool = False, raise_error: str | None = None):
        self.delay_s = delay_s
        self.raise_cancelled = raise_cancelled
        self.raise_error = raise_error
        self._ledger = FakeLedger()
        self.sent_texts: list[str] = []

    def send(self, user_text, cancel_token, on_reasoning_token=None, on_content_token=None):
        self.sent_texts.append(user_text)
        if on_reasoning_token:
            on_reasoning_token("思考中")
        if on_content_token:
            on_content_token("回答中")
        if self.delay_s and cancel_token.wait(timeout=self.delay_s):
            raise CancelledError("cancelled")
        if self.raise_cancelled:
            raise CancelledError("cancelled")
        if self.raise_error:
            raise RuntimeError(self.raise_error)
        usage = AIUsage(prompt_tokens=100, cached_prompt_tokens=20, completion_tokens=50, total_tokens=150)
        self._ledger.add(usage)
        return AIReply(
            content="这是回答",
            reasoning_content="这是推理",
            raw={"id": "req-1", "model": "fake-model", "usage": {}},
            usage=usage,
            request_id="req-1",
            latency_ms=12.3,
        )


@pytest.fixture
def build_app():
    def _build(session: FakeChatSession | None = None):
        application = FastAPI()
        application.include_router(chat_api.ws_router)
        state = AppState(
            ctx=None,
            orchestrator=None,
            analysis_runner=AnalysisRunner(None),
            chat_runner=ChatRunner(),
        )
        state.chat_session = session
        application.state.pa_state = state
        return application, state

    return _build


def _collect_until(ws, predicate, limit=50):
    messages = []
    for _ in range(limit):
        msg = ws.receive_json()
        messages.append(msg)
        if predicate(msg):
            return messages
    raise AssertionError(f"predicate never satisfied, got: {messages}")


def test_send_without_session_returns_error(build_app):
    app, _ = build_app(session=None)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "止损应该设多少？"})
        msg = ws.receive_json()
        assert msg["type"] == "chat_error"
        assert "尚无可继续追问" in msg["message"]


def test_send_success_streams_and_returns_done(build_app):
    session = FakeChatSession()
    app, _ = build_app(session=session)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "止损应该设多少？"})
        messages = _collect_until(ws, lambda m: m["type"] == "chat_done")
        types = [m["type"] for m in messages]
        assert "chat_reasoning" in types
        assert "chat_content" in types
        done = messages[-1]
        assert done["content"] == "这是回答"
        assert done["reasoning"] == "这是推理"
        assert done["usage"]["total_tokens"] == 150
        assert done["token_usage"]["context_used"] == 150
        assert session.sent_texts == ["止损应该设多少？"]


def test_empty_text_is_ignored(build_app):
    session = FakeChatSession()
    app, _ = build_app(session=session)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "   "})
        ws.send_json({"type": "send", "text": "真正的问题"})
        _collect_until(ws, lambda m: m["type"] == "chat_done")
        assert session.sent_texts == ["真正的问题"]


def test_cancel_before_completion_reports_cancelled(build_app):
    session = FakeChatSession(delay_s=0.3)
    app, _ = build_app(session=session)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "追问"})
        time.sleep(0.05)
        ws.send_json({"type": "cancel"})
        messages = _collect_until(ws, lambda m: m["type"] == "chat_error")
        assert messages[-1]["cancelled"] is True


def test_session_raises_generic_error(build_app):
    session = FakeChatSession(raise_error="API 积分不足")
    app, _ = build_app(session=session)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "追问"})
        messages = _collect_until(ws, lambda m: m["type"] == "chat_error")
        assert messages[-1]["message"] == "API 积分不足"
        assert messages[-1]["cancelled"] is False


def test_second_send_while_busy_is_rejected(build_app):
    session = FakeChatSession(delay_s=0.3)
    app, state = build_app(session=session)
    with TestClient(app) as client, client.websocket_connect("/ws/chat") as ws:
        ws.send_json({"type": "send", "text": "第一条"})
        time.sleep(0.05)
        ws.send_json({"type": "send", "text": "第二条"})
        messages = _collect_until(ws, lambda m: m["type"] == "chat_error")
        assert messages[-1]["message"] == "追问进行中"
        ws.send_json({"type": "cancel"})
        _collect_until(ws, lambda m: m["type"] == "chat_error")
