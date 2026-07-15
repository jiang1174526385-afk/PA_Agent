from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.records.schema import AnalysisRecord, RecordMeta
from pa_agent.webui.api import chat as chat_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner
from pa_agent.webui.services.chat_runner import ChatRunner


def _make_record(*, api_key_in_prompt: str = "", exception=None) -> AnalysisRecord:
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="FAKEUSD",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "fake-model"},
    )
    s1_user = "分析这段K线" + (f"\napi_key={api_key_in_prompt}" if api_key_in_prompt else "")
    return AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[
            {"role": "system", "content": "system-1"},
            {"role": "user", "content": s1_user},
        ],
        stage1_response={"id": "r1", "usage": {}},
        stage1_diagnosis=None if exception else {"gate_result": "proceed"},
        stage2_messages=[
            {"role": "system", "content": "system-2"},
            {"role": "user", "content": "第一轮 user"},
            {"role": "user", "content": "最后一轮 user"},
        ],
        stage2_response={"id": "r2", "usage": {}},
        stage2_decision=None if exception else {"order_type": "买入"},
        strategy_files_used=["strategy_a.txt"],
        experience_loaded=[{"id": "exp-1"}],
        exception=exception,
        usage_total={},
    )


@pytest.fixture
def build_app():
    def _build(api_key: str | None = None):
        application = FastAPI()
        application.include_router(chat_api.router, prefix="/api")
        ctx = SimpleNamespace(settings=SimpleNamespace(provider=SimpleNamespace(api_key=api_key or "")))
        state = AppState(
            ctx=ctx if api_key is not None else None,
            orchestrator=None,
            analysis_runner=AnalysisRunner(None),
            chat_runner=ChatRunner(),
        )
        application.state.pa_state = state
        return application

    return _build


def test_debug_context_returns_stage1_stage2_turns(build_app):
    app = build_app()
    record = _make_record()
    with TestClient(app) as client:
        resp = client.post("/api/chat/debug-context", json={"record": record.model_dump()})
    assert resp.status_code == 200
    body = resp.json()
    labels = [t["label"] for t in body["turns"]]
    assert labels == ["Stage1 诊断", "Stage2 决策"]
    assert body["turns"][0]["system_prompt"] == "system-1"
    assert body["turns"][1]["user_prompt"] == "最后一轮 user"  # last user message, not first
    assert body["prompt_files"]["stage2_files"] == ["strategy_a.txt"] or body["prompt_files"]["stage2_files"]
    assert body["prompt_files"]["experience_count"] == 1


def test_debug_context_includes_exception_turn(build_app):
    app = build_app()
    record = _make_record(exception={"stage": "stage2", "type": "validation_error", "message": "字段缺失"})
    with TestClient(app) as client:
        resp = client.post("/api/chat/debug-context", json={"record": record.model_dump()})
    body = resp.json()
    labels = [t["label"] for t in body["turns"]]
    assert labels == ["Stage1 诊断", "Stage2 决策", "⚠ 异常"]
    assert "字段缺失" in body["turns"][2]["validation_info"]
    assert "字段缺失" in body["turns"][1]["validation_info"]  # stage2 turn shows the exception detail


def test_debug_context_masks_api_key_in_prompts(build_app):
    app = build_app(api_key="sk-super-secret-key-1234")
    record = _make_record(api_key_in_prompt="sk-super-secret-key-1234")
    with TestClient(app) as client:
        resp = client.post("/api/chat/debug-context", json={"record": record.model_dump()})
    body = resp.json()
    s1_user = body["turns"][0]["user_prompt"]
    assert "sk-super-secret-key-1234" not in s1_user
    assert "1234" in s1_user  # mask_secret keeps the last 4 chars
