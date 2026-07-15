"""Trade-record analysis report API (phase 2): list/backfill/summary/orders.

Reads `trade_records/<symbol>_<timeframe>.csv` written by
`pa_agent/records/trade_logger.py`, back-filled with real MT5/OKX historical
fills via `pa_agent/records/trade_fill_backfill.py`. No AI decision logic is
touched here -- this module only reads/aggregates already-written records.
"""
from __future__ import annotations

import csv
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from pa_agent.config.settings import load_settings
from pa_agent.records.report_metrics import (
    compute_summary,
    equity_curve,
    holding_time_distribution,
    monthly_returns,
    pnl_calendar,
    rows_to_filled_trades,
    slippage_distribution,
    symbol_distribution,
)
from pa_agent.records.trade_fill_backfill import BackfillResult, backfill_csv
from pa_agent.webui.schemas.reports import (
    BackfillResponse,
    OrdersResponse,
    ReportListItem,
    ReportSummaryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_TRADE_RECORDS_DIR = Path("trade_records")


def _resolve_csv_path(key: str) -> Path:
    """Validate *key* against actual files on disk (no path traversal --
    reject any key that doesn't exactly match an existing `<key>.csv`)."""
    if "/" in key or "\\" in key or ".." in key:
        raise HTTPException(status_code=400, detail=f"非法 report key: {key!r}")
    path = _TRADE_RECORDS_DIR / f"{key}.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"未找到交易记录文件: {path}")
    return path


def _read_rows(csv_path: Path) -> list[dict[str, str]]:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


@router.get("/reports")
async def list_reports() -> list[ReportListItem]:
    if not _TRADE_RECORDS_DIR.exists():
        return []
    items = []
    for csv_path in sorted(_TRADE_RECORDS_DIR.glob("*.csv")):
        key = csv_path.stem
        symbol, _, timeframe = key.rpartition("_")
        try:
            row_count = sum(1 for _ in open(csv_path, encoding="utf-8-sig")) - 1
        except OSError:
            row_count = 0
        items.append(
            ReportListItem(key=key, symbol=symbol or key, timeframe=timeframe, row_count=max(0, row_count))
        )
    return items


@router.post("/reports/{key}/backfill")
async def trigger_backfill(key: str, kind: str = Query(..., pattern="^(mt5|okx)$")) -> BackfillResponse:
    csv_path = _resolve_csv_path(key)
    settings = load_settings()
    okx_credentials = None
    if kind == "okx":
        okx_credentials = {
            "api_key": settings.okx.api_key,
            "api_secret": settings.okx.api_secret,
            "passphrase": settings.okx.passphrase,
        }
        if not all(okx_credentials.values()):
            raise HTTPException(
                status_code=400,
                detail="OKX API Key/Secret/Passphrase 未配置，请先在设置里填写",
            )
    try:
        result: BackfillResult = backfill_csv(csv_path, kind, okx_credentials=okx_credentials)
    except Exception as exc:  # noqa: BLE001
        logger.error("backfill failed for %s: %s", key, exc, exc_info=True)
        raise HTTPException(status_code=502, detail=f"回填失败: {exc}") from exc
    return BackfillResponse(
        processed=result.processed,
        matched=result.matched,
        unmatched=result.unmatched,
        skipped_already_filled=result.skipped_already_filled,
    )


def _filter_rows(
    rows: list[dict[str, str]],
    *,
    date_from: str | None,
    date_to: str | None,
    strategy: str | None,
) -> list[dict[str, str]]:
    out = rows
    if date_from:
        out = [r for r in out if (r.get("record_time") or "") >= date_from]
    if date_to:
        out = [r for r in out if (r.get("record_time") or "") <= date_to]
    if strategy and strategy != "__all__":
        out = [r for r in out if r.get("decision_stance") == strategy]
    return out


@router.get("/reports/{key}/summary")
async def get_summary(
    key: str,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    strategy: str | None = None,
) -> ReportSummaryResponse:
    csv_path = _resolve_csv_path(key)
    rows = _filter_rows(_read_rows(csv_path), date_from=date_from, date_to=date_to, strategy=strategy)
    trades = rows_to_filled_trades(rows)
    summary = compute_summary(trades, as_of=datetime.now(timezone.utc))
    return ReportSummaryResponse(
        **summary.__dict__,
        equity_curve=equity_curve(trades),
        monthly_returns=monthly_returns(trades),
        symbol_distribution=symbol_distribution(trades),
        holding_time_distribution=holding_time_distribution(trades),
        slippage=slippage_distribution(trades),
    )


@router.get("/reports/{key}/calendar")
async def get_calendar(
    key: str,
    year: int,
    month: int,
    strategy: str | None = None,
) -> dict[str, float]:
    csv_path = _resolve_csv_path(key)
    rows = _filter_rows(_read_rows(csv_path), date_from=None, date_to=None, strategy=strategy)
    trades = rows_to_filled_trades(rows)
    return pnl_calendar(trades, year, month)


@router.get("/reports/{key}/orders")
async def get_orders(
    key: str,
    date_from: str | None = Query(None, alias="from"),
    date_to: str | None = Query(None, alias="to"),
    strategy: str | None = None,
    search: str | None = None,
    sort: str = "record_time_desc",
    page: int = 1,
    page_size: int = 10,
) -> OrdersResponse:
    csv_path = _resolve_csv_path(key)
    rows = _filter_rows(_read_rows(csv_path), date_from=date_from, date_to=date_to, strategy=strategy)

    if search:
        needle = search.lower()
        rows = [
            r for r in rows
            if needle in (r.get("symbol", "") + r.get("decision_stance", "") + r.get("reasoning", "")).lower()
        ]

    sort_key, _, direction = sort.rpartition("_")
    reverse = direction == "desc"
    if sort_key in ("record_time", "pnl_usd", "pnl_pips"):
        def _key(r: dict[str, Any]) -> Any:
            v = r.get(sort_key, "")
            if sort_key != "record_time":
                try:
                    return float(v or 0.0)
                except ValueError:
                    return 0.0
            return v
        rows = sorted(rows, key=_key, reverse=reverse)

    total = len(rows)
    start = (max(1, page) - 1) * page_size
    page_rows = rows[start : start + page_size]

    return OrdersResponse(total=total, page=page, page_size=page_size, rows=page_rows)
