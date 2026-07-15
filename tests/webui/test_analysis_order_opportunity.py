"""Integration test: a real /ws/analysis "full" submit whose stage-2 decision
qualifies as an order opportunity must broadcast `order_opportunity` and fire
the (mocked) feishu/pushplus notifiers -- see
pa_agent/webui/services/order_alert.py, wired into
pa_agent/webui/api/analysis.py::ws_analysis's `_run()`.
"""

from __future__ import annotations

from types import SimpleNamespace

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


def _make_opportunity_record() -> AnalysisRecord:
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
        stage1_diagnosis={"gate_result": "proceed"},
        stage2_messages=[],
        stage2_response=None,
        stage2_decision={
            "decision": {
                "order_type": "市价单",
                "order_direction": "做多",
                "trade_confidence": 88,
            },
        },
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


class _OpportunityOrchestrator:
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
        on_event(OrchestratorEvent.Stage1Started)
        on_event(OrchestratorEvent.Stage2Started)
        on_event(OrchestratorEvent.RecordSaved)
        return _make_opportunity_record()


def _collect_until(ws, predicate, limit=50):
    messages = []
    for _ in range(limit):
        msg = ws.receive_json()
        messages.append(msg)
        if predicate(msg):
            return messages
    raise AssertionError(f"predicate never satisfied, got: {messages}")


def test_full_submit_with_order_opportunity_broadcasts_and_notifies(monkeypatch):
    sent_feishu: list[dict] = []
    monkeypatch.setattr(
        "pa_agent.notify.feishu_notifier.send_order_signal",
        lambda **kw: sent_feishu.append(kw) or True,
    )
    monkeypatch.setattr(
        "pa_agent.notify.pushplus_notifier.pushplus_is_active", lambda settings=None: False
    )

    orchestrator = _OpportunityOrchestrator()
    app = FastAPI()
    app.include_router(analysis_api.ws_router)
    key = ("okx", "FAKEUSD", "15m")
    state = AppState(
        ctx=None, orchestrator=orchestrator, analysis_runner=AnalysisRunner(orchestrator)
    )
    state.active_kline_key = key
    state.broadcasters = {key: SimpleNamespace(latest_frame=_make_frame())}
    app.state.pa_state = state

    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "full"})
        messages = _collect_until(ws, lambda m: m["type"] == "order_opportunity")
        assert "做多" in messages[-1]["message"]

    import time

    deadline = time.monotonic() + 1.0
    while time.monotonic() < deadline and not sent_feishu:
        time.sleep(0.02)
    assert sent_feishu, "feishu notifier should have been called on a background thread"
    assert sent_feishu[0]["decision_inner"]["order_type"] == "市价单"
