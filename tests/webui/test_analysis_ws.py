from __future__ import annotations

import time
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.data.base import IndicatorBundle, KlineBar, KlineFrame
from pa_agent.records.schema import AnalysisRecord, RecordMeta
from pa_agent.util.threading import OrchestratorEvent
from pa_agent.webui.api import analysis as analysis_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner


def _make_frame() -> KlineFrame:
    bar = KlineBar(seq=1, ts_open=0.0, open=1.0, high=1.5, low=0.5, close=1.2, volume=10.0)
    return KlineFrame(
        symbol="FAKEUSD",
        timeframe="15m",
        bars=(bar,),
        indicators=IndicatorBundle(ema20=(1.1,), atr14=(0.2,)),
        snapshot_ts_local_ms=0,
    )


def _make_record(cancelled: bool = False) -> AnalysisRecord:
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="FAKEUSD",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "fake-model"},
    )
    return AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=None
        if cancelled
        else {
            "gate_result": "proceed",
            "gate_trace": [{"node_id": "1.1", "question": "q1", "answer": "是", "reason": "r1", "bar_range": "K3-K1"}],
        },
        stage2_messages=[],
        stage2_response=None,
        stage2_decision=None
        if cancelled
        else {
            "order_type": "买入",
            "trade_confidence": 80,
            "decision_trace": [{"node_id": "9.0", "question": "q2", "answer": "否", "reason": "r2", "bar_range": "K1"}],
            "terminal": {"node_id": "9.0", "outcome": "wait", "label": "等待"},
            "gate_shortcircuited": False,
        },
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


class FakeOrchestrator:
    """Synchronous fake mirroring TwoStageOrchestrator.submit()'s callback contract."""

    def __init__(self, delay_s: float = 0.05):
        self.delay_s = delay_s
        self.submit_calls: list[dict] = []

    def submit(
        self,
        frame,
        cancel_token,
        on_event,
        *,
        on_stage1_reasoning=None,
        on_stage1_content=None,
        on_stage2_reasoning=None,
        on_stage2_content=None,
        on_stage_prompt=None,
        on_stage2_files=None,
        previous_record=None,
        incremental_new_bar_count=None,
    ):
        self.submit_calls.append(
            {
                "previous_record": previous_record,
                "incremental_new_bar_count": incremental_new_bar_count,
            }
        )
        on_event(OrchestratorEvent.Stage1Started)
        on_stage1_reasoning("s1-reasoning-chunk")
        on_stage1_content("s1-content-chunk")

        if cancel_token.wait(timeout=self.delay_s):
            on_event(OrchestratorEvent.Cancelled)
            return _make_record(cancelled=True)

        on_event(OrchestratorEvent.Stage1Done)
        on_stage_prompt("stage2", "system-prompt", "user-prompt")
        on_stage2_files(["strategy_a.txt"])
        on_event(OrchestratorEvent.Stage2Started)
        on_stage2_reasoning("s2-reasoning-chunk")
        on_stage2_content("s2-content-chunk")
        on_event(OrchestratorEvent.Stage2Done)
        on_event(OrchestratorEvent.RecordSaved)
        return _make_record()


@pytest.fixture
def build_app():
    def _build(delay_s: float = 0.05):
        orchestrator = FakeOrchestrator(delay_s=delay_s)
        application = FastAPI()
        application.include_router(analysis_api.ws_router)
        key = ("okx", "FAKEUSD", "15m")
        state = AppState(
            ctx=None, orchestrator=orchestrator, analysis_runner=AnalysisRunner(orchestrator)
        )
        state.active_kline_key = key
        state.broadcasters = {key: SimpleNamespace(latest_frame=_make_frame())}
        application.state.pa_state = state
        return application, orchestrator, state

    return _build


def _collect_until(ws, predicate, limit=50):
    messages = []
    for _ in range(limit):
        msg = ws.receive_json()
        messages.append(msg)
        if predicate(msg):
            return messages
    raise AssertionError(f"predicate never satisfied, got: {messages}")


def test_submit_full_analysis_message_sequence(build_app):
    app, orchestrator, _ = build_app(delay_s=0.0)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "full"})
        messages = _collect_until(ws, lambda m: m["type"] == "record")

        types = [m["type"] for m in messages]
        assert "stage1_reasoning" in types
        assert "stage1_content" in types
        assert "stage_prompt" in types
        assert "stage2_files" in types
        assert "stage2_reasoning" in types
        assert "stage2_content" in types
        record_msg = messages[-1]
        assert record_msg["record"]["stage2_decision"]["order_type"] == "买入"
        assert orchestrator.submit_calls[0]["previous_record"] is None

        # phase 3: /ws/analysis must transparently forward gate_trace/decision_trace/
        # terminal inside stage1_diagnosis/stage2_decision -- AnalysisRecord.model_dump()
        # is a plain dict pass-through (see docs/webui_migration/phase-3-execution-plan.md §3.5).
        record = record_msg["record"]
        assert record["stage1_diagnosis"]["gate_trace"][0]["node_id"] == "1.1"
        assert record["stage2_decision"]["decision_trace"][0]["node_id"] == "9.0"
        assert record["stage2_decision"]["terminal"]["outcome"] == "wait"


def test_submit_incremental_passes_previous_record(build_app):
    app, orchestrator, state = build_app(delay_s=0.0)
    prev = _make_record()
    state.last_analysis_record = prev
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "incremental", "incremental_new_bar_count": 3})
        _collect_until(ws, lambda m: m["type"] == "record")

    assert orchestrator.submit_calls[0]["previous_record"] is prev
    assert orchestrator.submit_calls[0]["incremental_new_bar_count"] == 3


def test_cancel_sets_cancel_token_and_returns_cancelled_record(build_app):
    app, _orchestrator, _ = build_app(delay_s=0.3)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "full"})
        # give the orchestrator thread time to start waiting on the cancel token
        time.sleep(0.05)
        ws.send_json({"type": "cancel"})
        messages = _collect_until(ws, lambda m: m["type"] == "record")
        events = [m["message"] for m in messages if m["type"] == "event"]
        assert "已取消" in events
        assert messages[-1]["record"]["stage2_decision"] is None


def test_second_submit_while_busy_is_rejected(build_app):
    app, _orchestrator, _ = build_app(delay_s=0.3)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "full"})
        time.sleep(0.05)
        ws.send_json({"type": "submit", "mode": "full"})
        messages = _collect_until(ws, lambda m: m["type"] == "error")
        assert messages[-1] == {"type": "error", "message": "分析进行中"}
        ws.send_json({"type": "cancel"})
        _collect_until(ws, lambda m: m["type"] == "record")


def test_submit_without_active_frame_errors(build_app):
    app, _, state = build_app()
    state.active_kline_key = None
    state.broadcasters = {}
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "full"})
        msg = ws.receive_json()
        assert msg["type"] == "error"
        assert "K线" in msg["message"]
