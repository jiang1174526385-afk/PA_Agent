"""Pure aggregation functions over back-filled trade CSV rows (phase 2 reports page).

Every formula here is the one from
`docs/webui_migration/phase-2-execution-plan.md` §5.3, with one deliberate
deviation confirmed with the user during implementation: **no "收益率%"
(return-on-capital) is computed** because no initial-capital/account-balance
history exists anywhere in this project (CSV, MT5, or OKX config) to serve as
the denominator, and fabricating one was explicitly disallowed by the
execution plan's §9 stop condition. Only absolute-USD figures are reported
(total P&L, drawdown in USD). "Max drawdown %" here is peak-to-trough as a
fraction of the peak cumulative-P&L value itself (a common alternative
definition that doesn't require a starting-capital base), not % of equity.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class FilledTrade:
    symbol: str
    direction: str  # order_direction, raw string from CSV
    entry_price: float | None
    actual_entry_price: float
    pnl_usd: float
    pnl_pips: float
    holding_duration_s: int
    win_loss: str  # "win" | "loss" | "breakeven"
    closed_at: datetime
    strategy: str  # decision_stance or model, used as a stand-in "strategy" label


def _is_long(direction: str) -> bool:
    d = (direction or "").lower()
    return "short" not in d and "做空" not in d


def rows_to_filled_trades(rows: list[dict[str, str]]) -> list[FilledTrade]:
    """Filter to `fill_status == "filled"` rows and parse into `FilledTrade`s,
    sorted by `closed_at` ascending (the ordering every metric below assumes)."""
    trades: list[FilledTrade] = []
    for row in rows:
        if (row.get("fill_status") or "").strip() != "filled":
            continue
        closed_at_raw = row.get("closed_at", "")
        if not closed_at_raw:
            continue
        try:
            closed_at = datetime.fromisoformat(closed_at_raw)
        except ValueError:
            continue
        try:
            pnl_usd = float(row.get("pnl_usd") or 0.0)
            pnl_pips = float(row.get("pnl_pips") or 0.0)
            holding_s = int(float(row.get("holding_duration_s") or 0))
        except ValueError:
            continue
        entry_price = None
        try:
            entry_price = float(row.get("entry_price") or "") or None
        except ValueError:
            entry_price = None
        trades.append(
            FilledTrade(
                symbol=row.get("symbol", ""),
                direction=row.get("order_direction", ""),
                entry_price=entry_price,
                actual_entry_price=float(row.get("actual_entry_price") or 0.0),
                pnl_usd=pnl_usd,
                pnl_pips=pnl_pips,
                holding_duration_s=holding_s,
                win_loss=row.get("win_loss", ""),
                closed_at=closed_at,
                strategy=row.get("decision_stance", "") or row.get("model", ""),
            )
        )
    trades.sort(key=lambda t: t.closed_at)
    return trades


@dataclass
class ReportSummary:
    total_pnl_usd: float
    max_drawdown_usd: float
    max_drawdown_pct: float | None  # None when peak <= 0 (undefined)
    profit_factor: float | None  # None when no losing trades
    win_rate_pct: float
    win_count: int
    loss_count: int
    long_win_rate_pct: float | None
    short_win_rate_pct: float | None
    avg_win_loss_ratio: float | None
    trade_count: int
    avg_trades_per_day: float
    max_consecutive_losses: int
    stagnation_days: int
    long_net_pnl_usd: float
    short_net_pnl_usd: float


def compute_summary(trades: list[FilledTrade], *, as_of: datetime | None = None) -> ReportSummary:
    if not trades:
        return ReportSummary(
            total_pnl_usd=0.0, max_drawdown_usd=0.0, max_drawdown_pct=None,
            profit_factor=None, win_rate_pct=0.0, win_count=0, loss_count=0,
            long_win_rate_pct=None, short_win_rate_pct=None, avg_win_loss_ratio=None,
            trade_count=0, avg_trades_per_day=0.0, max_consecutive_losses=0,
            stagnation_days=0, long_net_pnl_usd=0.0, short_net_pnl_usd=0.0,
        )

    as_of = as_of or trades[-1].closed_at

    total_pnl = sum(t.pnl_usd for t in trades)

    # Equity curve = cumulative pnl_usd by closed_at order; drawdown from running peak.
    cum = 0.0
    peak = 0.0
    max_dd_usd = 0.0
    max_dd_pct = 0.0
    peak_at_max_dd = 0.0
    for t in trades:
        cum += t.pnl_usd
        if cum > peak:
            peak = cum
        dd = peak - cum
        if dd > max_dd_usd:
            max_dd_usd = dd
            peak_at_max_dd = peak
    max_dd_pct_val: float | None = (max_dd_usd / peak_at_max_dd) if peak_at_max_dd > 0 else None

    wins = [t for t in trades if t.win_loss == "win"]
    losses = [t for t in trades if t.win_loss == "loss"]
    win_count, loss_count = len(wins), len(losses)
    win_rate = (win_count / (win_count + loss_count) * 100.0) if (win_count + loss_count) else 0.0

    def _dir_win_rate(is_long: bool) -> float | None:
        subset = [t for t in trades if _is_long(t.direction) == is_long and t.win_loss in ("win", "loss")]
        if not subset:
            return None
        w = sum(1 for t in subset if t.win_loss == "win")
        return w / len(subset) * 100.0

    long_win_rate = _dir_win_rate(True)
    short_win_rate = _dir_win_rate(False)

    gross_profit = sum(t.pnl_usd for t in wins)
    gross_loss = sum(t.pnl_usd for t in losses)  # negative
    profit_factor = (gross_profit / abs(gross_loss)) if gross_loss < 0 else None

    avg_win = (gross_profit / win_count) if win_count else 0.0
    avg_loss = (abs(gross_loss) / loss_count) if loss_count else 0.0
    avg_win_loss_ratio = (avg_win / avg_loss) if avg_loss > 0 else None

    span_days = max(1, (as_of.date() - trades[0].closed_at.date()).days + 1)
    avg_trades_per_day = len(trades) / span_days

    # Longest consecutive run of win_loss == "loss"
    max_consec = cur_consec = 0
    for t in trades:
        if t.win_loss == "loss":
            cur_consec += 1
            max_consec = max(max_consec, cur_consec)
        else:
            cur_consec = 0

    # Stagnation: days since the last new equity high (peak), up to `as_of`.
    cum2 = 0.0
    peak2 = float("-inf")
    peak_date = trades[0].closed_at.date()
    for t in trades:
        cum2 += t.pnl_usd
        if cum2 >= peak2:
            peak2 = cum2
            peak_date = t.closed_at.date()
    stagnation_days = (as_of.date() - peak_date).days

    long_net = sum(t.pnl_usd for t in trades if _is_long(t.direction))
    short_net = sum(t.pnl_usd for t in trades if not _is_long(t.direction))

    return ReportSummary(
        total_pnl_usd=total_pnl,
        max_drawdown_usd=max_dd_usd,
        max_drawdown_pct=max_dd_pct_val,
        profit_factor=profit_factor,
        win_rate_pct=win_rate,
        win_count=win_count,
        loss_count=loss_count,
        long_win_rate_pct=long_win_rate,
        short_win_rate_pct=short_win_rate,
        avg_win_loss_ratio=avg_win_loss_ratio,
        trade_count=len(trades),
        avg_trades_per_day=avg_trades_per_day,
        max_consecutive_losses=max_consec,
        stagnation_days=max(0, stagnation_days),
        long_net_pnl_usd=long_net,
        short_net_pnl_usd=short_net,
    )


def equity_curve(trades: list[FilledTrade]) -> list[dict]:
    cum = 0.0
    points = []
    for t in trades:
        cum += t.pnl_usd
        points.append({"ts": t.closed_at.isoformat(), "equity_usd": cum})
    return points


def monthly_returns(trades: list[FilledTrade]) -> list[dict]:
    buckets: dict[str, float] = {}
    for t in trades:
        key = t.closed_at.strftime("%Y-%m")
        buckets[key] = buckets.get(key, 0.0) + t.pnl_usd
    return [{"month": k, "pnl_usd": v} for k, v in sorted(buckets.items())]


def symbol_distribution(trades: list[FilledTrade]) -> list[dict]:
    buckets: dict[str, float] = {}
    for t in trades:
        buckets[t.symbol] = buckets.get(t.symbol, 0.0) + abs(t.pnl_usd)
    total = sum(buckets.values()) or 1.0
    return [
        {"symbol": k, "abs_pnl_usd": v, "pct": v / total * 100.0}
        for k, v in sorted(buckets.items(), key=lambda kv: -kv[1])
    ]


def pnl_calendar(trades: list[FilledTrade], year: int, month: int) -> dict[str, float]:
    out: dict[str, float] = {}
    for t in trades:
        if t.closed_at.year == year and t.closed_at.month == month:
            key = t.closed_at.strftime("%Y-%m-%d")
            out[key] = out.get(key, 0.0) + t.pnl_usd
    return out


_HOLDING_BUCKETS = [
    ("<=15min", 0, 15 * 60),
    ("15-60min", 15 * 60, 60 * 60),
    ("1-2h", 60 * 60, 2 * 3600),
    ("2-4h", 2 * 3600, 4 * 3600),
    (">4h", 4 * 3600, float("inf")),
]


def holding_time_distribution(trades: list[FilledTrade]) -> list[dict]:
    counts = {label: 0 for label, _, _ in _HOLDING_BUCKETS}
    for t in trades:
        for label, lo, hi in _HOLDING_BUCKETS:
            if lo <= t.holding_duration_s < hi:
                counts[label] += 1
                break
    total = sum(counts.values()) or 1
    return [
        {"bucket": label, "count": counts[label], "pct": counts[label] / total * 100.0}
        for label, _, _ in _HOLDING_BUCKETS
    ]


def slippage_distribution(trades: list[FilledTrade]) -> dict:
    """Slippage = actual_entry_price - planned entry_price, signed by direction
    (positive = filled better than planned), in the same price units as the CSV
    (not converted to "points" -- no per-symbol point-value table exists in
    this project to do that conversion generically)."""
    slippages = []
    for t in trades:
        if t.entry_price is None:
            continue
        raw = t.actual_entry_price - t.entry_price
        slippages.append(raw if _is_long(t.direction) else -raw)
    if not slippages:
        return {"avg": None, "median": None, "buckets": []}
    slippages.sort()
    n = len(slippages)
    median = slippages[n // 2] if n % 2 else (slippages[n // 2 - 1] + slippages[n // 2]) / 2
    avg = sum(slippages) / n
    bucket_edges = [5, 15, 25, 35, float("inf")]
    labels = ["+5", "+15", "+25", "+35", ">=+40"]
    counts = [0] * len(labels)
    for s in slippages:
        for i, edge in enumerate(bucket_edges):
            if s < edge:
                counts[i] += 1
                break
        else:
            counts[-1] += 1
    return {
        "avg": avg,
        "median": median,
        "buckets": [{"label": labels[i], "count": counts[i]} for i in range(len(labels))],
    }
