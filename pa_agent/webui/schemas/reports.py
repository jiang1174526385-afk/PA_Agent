"""Response DTOs for the phase-2 trade-record report API."""
from __future__ import annotations

from pydantic import BaseModel


class ReportListItem(BaseModel):
    key: str  # "<symbol>_<timeframe>" -- also the CSV filename stem
    symbol: str
    timeframe: str
    row_count: int


class BackfillResponse(BaseModel):
    processed: int
    matched: int
    unmatched: int
    skipped_already_filled: int


class KpiValue(BaseModel):
    value: float | None
    sub_label: str | None = None


class ReportSummaryResponse(BaseModel):
    total_pnl_usd: float
    max_drawdown_usd: float
    max_drawdown_pct: float | None
    profit_factor: float | None
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
    equity_curve: list[dict]
    monthly_returns: list[dict]
    symbol_distribution: list[dict]
    holding_time_distribution: list[dict]
    slippage: dict


class OrderRow(BaseModel):
    record_time: str
    symbol: str
    order_direction: str
    entry_price: str
    actual_exit_price: str
    pnl_usd: str
    pnl_pips: str
    holding_duration_s: str
    decision_stance: str
    fill_status: str
    win_loss: str


class OrdersResponse(BaseModel):
    total: int
    page: int
    page_size: int
    rows: list[dict]
