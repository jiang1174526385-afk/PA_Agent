from __future__ import annotations

from pa_agent.records.schema import AnalysisRecord, RecordMeta
from pa_agent.webui.services.trade_metrics_view import build_trade_metrics


def _meta(decision_stance: str = "conservative") -> RecordMeta:
    return RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="FAKEUSD",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "fake"},
        decision_stance=decision_stance,
    )


def _record(stage2_decision: dict | None) -> AnalysisRecord:
    return AnalysisRecord(
        meta=_meta(),
        kline_data=[],
        htf_text="",
        stage1_messages=[],
        stage1_response=None,
        stage1_diagnosis=None,
        stage2_messages=[],
        stage2_response=None,
        stage2_decision=stage2_decision,
        strategy_files_used=[],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )


def test_none_record_returns_none():
    assert build_trade_metrics(None) is None


def test_real_nested_shape_full_fields_computed():
    record = _record(
        {
            "decision": {
                "order_type": "限价单",
                "order_direction": "做多",
                "entry_price": 100.0,
                "take_profit_price": 110.0,
                "stop_loss_price": 95.0,
                "estimated_win_rate": "65",
            },
        }
    )

    metrics = build_trade_metrics(record)

    assert metrics is not None
    # risk = 5, reward = 10 -> ratio 2.0
    assert metrics["risk_reward_ratio"] == 2.0
    assert metrics["risk_reward_text"] == "2.00 : 1"
    assert metrics["estimated_win_rate_pct"] == 65
    assert metrics["trader_equation_passed"] is True
    assert metrics["min_risk_reward_ratio"] == 1.0
    assert metrics["max_risk_reward_ratio"] == 1.0


def test_flat_fixture_shape_also_computed():
    record = _record(
        {
            "order_type": "突破单",
            "order_direction": "做空",
            "entry_price": 100.0,
            "take_profit_price": 90.0,
            "stop_loss_price": 105.0,
            "estimated_win_rate": 70,
        }
    )

    metrics = build_trade_metrics(record)

    assert metrics is not None
    assert metrics["risk_reward_ratio"] == 2.0
    assert metrics["estimated_win_rate_pct"] == 70


def test_no_order_type_returns_none_overall():
    record = _record({"order_type": "不下单"})
    assert build_trade_metrics(record) is None


def test_missing_price_fields_returns_none_overall_for_no_order():
    # order_type "不下单" is the only "nothing to evaluate" case per spec;
    # missing prices with a real order_type still return a dict (ratio null).
    record = _record({"order_type": "不下单", "order_direction": "做多"})
    assert build_trade_metrics(record) is None


def test_missing_win_rate_leaves_ratio_but_nulls_equation():
    record = _record(
        {
            "order_type": "市价单",
            "order_direction": "做多",
            "entry_price": 100.0,
            "take_profit_price": 110.0,
            "stop_loss_price": 95.0,
        }
    )

    metrics = build_trade_metrics(record)

    assert metrics is not None
    assert metrics["risk_reward_ratio"] == 2.0
    assert metrics["estimated_win_rate_pct"] is None
    assert metrics["trader_equation_passed"] is None


def test_invalid_prices_null_ratio_but_min_max_still_present():
    record = _record(
        {
            "order_type": "市价单",
            "order_direction": "做多",
            "entry_price": 100.0,
            "take_profit_price": 90.0,  # invalid geometry for a long
            "stop_loss_price": 95.0,
            "estimated_win_rate": 60,
        }
    )

    metrics = build_trade_metrics(record)

    assert metrics is not None
    assert metrics["risk_reward_ratio"] is None
    assert metrics["risk_reward_text"] is None
    assert metrics["trader_equation_passed"] is None
    assert metrics["min_risk_reward_ratio"] == 1.0
    assert metrics["max_risk_reward_ratio"] == 1.0


def test_missing_decision_key_and_non_dict_returns_none():
    assert build_trade_metrics(_record(None)) is None
