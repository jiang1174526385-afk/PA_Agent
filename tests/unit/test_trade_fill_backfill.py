from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pa_agent.records.report_metrics import (
    FilledTrade,
    compute_summary,
    holding_time_distribution,
    monthly_returns,
    rows_to_filled_trades,
    slippage_distribution,
    symbol_distribution,
)


def _trade(pnl_usd: float, *, day_offset: int, direction: str = "做多",
           entry_price: float | None = 100.0, actual_entry_price: float = 100.0,
           holding_s: int = 900, win_loss: str | None = None) -> FilledTrade:
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    if win_loss is None:
        win_loss = "win" if pnl_usd > 0 else ("loss" if pnl_usd < 0 else "breakeven")
    return FilledTrade(
        symbol="XAUUSDm", direction=direction, entry_price=entry_price,
        actual_entry_price=actual_entry_price, pnl_usd=pnl_usd, pnl_pips=pnl_usd / 10,
        holding_duration_s=holding_s, win_loss=win_loss,
        closed_at=base + timedelta(days=day_offset), strategy="balanced",
    )


def test_max_drawdown_known_sequence():
    # equity path: 0 -> 100 -> 60 -> 150 -> 90
    trades = [_trade(100, day_offset=0), _trade(-40, day_offset=1),
              _trade(90, day_offset=2), _trade(-60, day_offset=3)]
    summary = compute_summary(trades)
    # peak 100 -> trough 60 (dd 40); peak 150 -> trough 90 (dd 60) -> max dd usd = 60
    assert summary.max_drawdown_usd == 60
    assert summary.max_drawdown_pct == 60 / 150


def test_profit_factor_and_win_rate():
    trades = [_trade(100, day_offset=0), _trade(-50, day_offset=1), _trade(50, day_offset=2)]
    summary = compute_summary(trades)
    assert summary.win_count == 2
    assert summary.loss_count == 1
    assert summary.profit_factor == 150 / 50
    assert round(summary.win_rate_pct, 2) == round(2 / 3 * 100, 2)


def test_no_losses_profit_factor_is_none():
    trades = [_trade(10, day_offset=0), _trade(20, day_offset=1)]
    summary = compute_summary(trades)
    assert summary.profit_factor is None


def test_max_consecutive_losses():
    trades = [
        _trade(10, day_offset=0), _trade(-5, day_offset=1), _trade(-5, day_offset=2),
        _trade(-5, day_offset=3), _trade(10, day_offset=4), _trade(-5, day_offset=5),
    ]
    summary = compute_summary(trades)
    assert summary.max_consecutive_losses == 3


def test_stagnation_days_since_last_new_high():
    trades = [_trade(100, day_offset=0), _trade(-10, day_offset=3), _trade(-5, day_offset=6)]
    as_of = trades[0].closed_at + timedelta(days=10)
    summary = compute_summary(trades, as_of=as_of)
    # last new high was day 0 -> stagnation = 10 days
    assert summary.stagnation_days == 10


def test_long_short_win_rates_split_by_direction():
    trades = [
        _trade(10, day_offset=0, direction="做多"),
        _trade(-10, day_offset=1, direction="做多"),
        _trade(10, day_offset=2, direction="做空"),
        _trade(10, day_offset=3, direction="做空"),
    ]
    summary = compute_summary(trades)
    assert summary.long_win_rate_pct == 50.0
    assert summary.short_win_rate_pct == 100.0


def test_holding_time_distribution_buckets():
    trades = [
        _trade(1, day_offset=0, holding_s=300),      # <=15min
        _trade(1, day_offset=1, holding_s=1800),     # 15-60min
        _trade(1, day_offset=2, holding_s=5400),     # 1-2h
        _trade(1, day_offset=3, holding_s=10800),    # 2-4h
        _trade(1, day_offset=4, holding_s=20000),    # >4h
    ]
    dist = holding_time_distribution(trades)
    counts = {d["bucket"]: d["count"] for d in dist}
    assert counts["<=15min"] == 1
    assert counts["15-60min"] == 1
    assert counts["1-2h"] == 1
    assert counts["2-4h"] == 1
    assert counts[">4h"] == 1


def test_slippage_distribution_direction_aware():
    # long trade filled 2 higher than planned = positive slippage;
    # short trade filled 2 lower than planned = positive slippage too.
    trades = [
        _trade(1, day_offset=0, direction="做多", entry_price=100.0, actual_entry_price=102.0),
        _trade(1, day_offset=1, direction="做空", entry_price=100.0, actual_entry_price=98.0),
    ]
    result = slippage_distribution(trades)
    assert result["avg"] == 2.0


def test_monthly_returns_groups_by_month():
    trades = [_trade(10, day_offset=0), _trade(20, day_offset=40)]
    result = monthly_returns(trades)
    assert len(result) == 2


def test_symbol_distribution_pct_sums_to_100():
    trades = [_trade(10, day_offset=0), _trade(-30, day_offset=1)]
    result = symbol_distribution(trades)
    assert round(sum(d["pct"] for d in result), 5) == 100.0


def test_rows_to_filled_trades_skips_unfilled_rows():
    rows = [
        {"fill_status": "unfilled", "closed_at": ""},
        {"fill_status": "filled", "closed_at": "2026-01-01T00:00:00+00:00",
         "pnl_usd": "10", "pnl_pips": "1", "holding_duration_s": "60",
         "win_loss": "win", "symbol": "X", "order_direction": "做多",
         "entry_price": "1", "actual_entry_price": "1", "decision_stance": "balanced"},
    ]
    trades = rows_to_filled_trades(rows)
    assert len(trades) == 1
    assert trades[0].pnl_usd == 10.0


def test_compute_summary_empty_trades_returns_zeros():
    summary = compute_summary([])
    assert summary.trade_count == 0
    assert summary.total_pnl_usd == 0.0
    assert summary.max_drawdown_pct is None
