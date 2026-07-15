from __future__ import annotations

import asyncio
from types import SimpleNamespace

from pa_agent.records.schema import AnalysisRecord, RecordMeta
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner
from pa_agent.webui.services.order_alert import maybe_alert_order_opportunity


class _FakeWebSocket:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, message: dict) -> None:
        self.sent.append(message)


def _make_record(
    *, order_type: str = "限价单", trade_confidence: int = 90, order_direction: str = "做多"
) -> AnalysisRecord:
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="FAKEUSD",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "fake"},
    )
    # Real production shape: order_type/order_direction/etc. nested under
    # "decision" (see pa_agent/ai/prompt_assembler.py's stage-2 output contract).
    return AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=None,
        stage2_messages=[],
        stage2_response=None,
        stage2_decision={
            "decision": {
                "order_type": order_type,
                "order_direction": order_direction,
                "entry_price": 100.0,
                "trade_confidence": trade_confidence,
            },
        },
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


def _make_state(*, alert_enabled: bool = True, threshold: int = 0) -> AppState:
    ctx = SimpleNamespace(
        settings=SimpleNamespace(
            general=SimpleNamespace(
                alert_on_order_opportunity=alert_enabled,
                decision_confidence_threshold=threshold,
            )
        )
    )
    return AppState(ctx=ctx, orchestrator=None, analysis_runner=AnalysisRunner(None))


async def _wait_until(predicate, timeout_s: float = 1.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout_s
    while asyncio.get_event_loop().time() < deadline:
        if predicate():
            return
        await asyncio.sleep(0.02)
    raise AssertionError("condition never became true")


async def test_alert_sent_and_notify_triggered_for_order_type(monkeypatch):
    sent_feishu: list[dict] = []
    sent_pushplus: list[dict] = []
    monkeypatch.setattr(
        "pa_agent.notify.feishu_notifier.send_order_signal",
        lambda **kw: sent_feishu.append(kw) or True,
    )
    monkeypatch.setattr(
        "pa_agent.notify.pushplus_notifier.pushplus_is_active", lambda settings=None: True
    )
    monkeypatch.setattr(
        "pa_agent.notify.pushplus_notifier.send_order_signal",
        lambda **kw: sent_pushplus.append(kw) or True,
    )

    ws = _FakeWebSocket()
    state = _make_state()
    record = _make_record()

    await maybe_alert_order_opportunity(ws, state, record)

    assert ws.sent[0]["type"] == "order_opportunity"
    assert "做多" in ws.sent[0]["message"]

    await _wait_until(lambda: bool(sent_feishu) and bool(sent_pushplus))
    assert sent_feishu[0]["decision_inner"]["order_type"] == "限价单"
    assert sent_feishu[0]["symbol"] == "FAKEUSD"
    assert sent_pushplus[0]["timeframe"] == "15m"


async def test_no_alert_when_order_type_not_opportunity(monkeypatch):
    called: list[dict] = []
    monkeypatch.setattr(
        "pa_agent.notify.feishu_notifier.send_order_signal", lambda **kw: called.append(kw)
    )
    ws = _FakeWebSocket()
    state = _make_state()
    record = _make_record(order_type="不下单")

    await maybe_alert_order_opportunity(ws, state, record)

    assert ws.sent == []
    await asyncio.sleep(0.05)
    assert called == []


async def test_no_alert_when_disabled_in_settings():
    ws = _FakeWebSocket()
    state = _make_state(alert_enabled=False)
    record = _make_record()

    await maybe_alert_order_opportunity(ws, state, record)

    assert ws.sent == []


async def test_confidence_threshold_gates_alert():
    ws = _FakeWebSocket()
    state = _make_state(threshold=95)
    record = _make_record(trade_confidence=90)

    await maybe_alert_order_opportunity(ws, state, record)

    assert ws.sent == []


async def test_no_alert_when_record_is_none():
    ws = _FakeWebSocket()
    state = _make_state()

    await maybe_alert_order_opportunity(ws, state, None)

    assert ws.sent == []


async def test_flat_stage2_decision_shape_also_supported():
    """The webui test-fixture convention (no nested "decision" key -- see
    tests/webui/conftest.py::_make_record / e2e/conftest.py::_build_record)
    must also be handled, since it's what every other phase's fake
    orchestrator produces."""
    ws = _FakeWebSocket()
    state = _make_state()
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="FAKEUSD",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "fake"},
    )
    record = AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=None,
        stage2_messages=[],
        stage2_response=None,
        stage2_decision={"order_type": "突破单", "order_direction": "做空", "trade_confidence": 80},
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )

    await maybe_alert_order_opportunity(ws, state, record)

    assert ws.sent[0]["type"] == "order_opportunity"
