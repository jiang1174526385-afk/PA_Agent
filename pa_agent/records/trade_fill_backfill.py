"""Back-fill real historical-fill results onto `trade_records/<symbol>_<tf>.csv`.

Each CSV row is an AI *plan* snapshot (`pa_agent/records/trade_logger.py`) with
no record of whether/when/how it was actually filled. This module appends
that missing information by querying real MT5/OKX historical deals/positions
(`pa_agent/data/trade_history.py`) -- never K-line-simulated fills, per
`docs/webui_migration/phase-2-execution-plan.md` §0.

Matching window
----------------
For CSV row *i*, the lookup window is
``[record_time_i, record_time_{i+1})`` -- i.e. up to the next plan for the
same symbol/timeframe, since a new plan supersedes the previous one. The last
row's window extends to "now", capped at `_MAX_LOOKAHEAD_DAYS` to bound query
size. This is the natural boundary implied by the CSV's own append-only
structure (one row per new decision), not an arbitrary constant -- see
completion report for the explicit callout to the user.

Matching rule (simplified per user decision, phase-2 session)
---------------------------------------------------------------
No price-tolerance exact/fuzzy tiers: user chose to skip that distinction for
this phase (no defensible tolerance value existed). A row is `filled` if a
same-symbol, same-direction closed round-trip trade is found inside its
window; `match_confidence` is a plain `matched`/`unmatched` binary, not the
`exact`/`fuzzy`/`unmatched` three-way split originally sketched in the
execution plan.

This module has no Web/API dependency and can be called from a CLI or cron
job as well as `pa_agent/webui/api/reports.py`.
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Literal

from pa_agent.data.base import DataSourceTransientError

logger = logging.getLogger(__name__)

_MAX_LOOKAHEAD_DAYS = 30

FILL_COLUMNS = [
    "fill_status",
    "actual_entry_price",
    "actual_exit_price",
    "filled_at",
    "closed_at",
    "pnl_usd",
    "pnl_pips",
    "holding_duration_s",
    "win_loss",
    "match_confidence",
]


@dataclass
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    skipped_already_filled: int


def _parse_record_time(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)


def _is_long(order_direction: str) -> bool:
    d = (order_direction or "").lower()
    return "short" not in d and "做空" not in d


def _read_csv(csv_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with open(csv_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        rows = list(reader)
    return fieldnames, rows


def _write_csv(csv_path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in fieldnames})


def _match_mt5_round_trip(
    symbol: str,
    is_long: bool,
    window_start_ms: int,
    window_end_ms: int,
    fetch: Callable[[str, int, int], list[dict]],
) -> dict | None:
    """Find the first complete in->out round trip for *symbol* in the window.

    MT5 deal `entry`: 0=IN (open), 1=OUT (close). Pairs are grouped by
    `position_id` (the position ticket shared by its opening and closing deals).
    """
    deals = fetch(symbol, window_start_ms, window_end_ms)
    if not deals:
        return None
    deals = sorted(deals, key=lambda d: d.get("time_msc") or (d.get("time", 0) * 1000))

    by_position: dict[int, list[dict]] = {}
    for d in deals:
        pos_id = d.get("position_id")
        if pos_id is None:
            continue
        by_position.setdefault(pos_id, []).append(d)

    # MT5 deal type: 0=BUY, 1=SELL. An opening BUY deal = long position.
    wanted_open_type = 0 if is_long else 1

    for pos_deals in by_position.values():
        opens = [d for d in pos_deals if d.get("entry") == 0 and d.get("type") == wanted_open_type]
        closes = [d for d in pos_deals if d.get("entry") == 1]
        if not opens or not closes:
            continue
        open_deal = opens[0]
        close_deal = closes[-1]
        return {
            "actual_entry_price": float(open_deal.get("price", 0.0)),
            "actual_exit_price": float(close_deal.get("price", 0.0)),
            "filled_at_ms": int(open_deal.get("time_msc") or open_deal.get("time", 0) * 1000),
            "closed_at_ms": int(close_deal.get("time_msc") or close_deal.get("time", 0) * 1000),
            "pnl_usd": float(close_deal.get("profit", 0.0)),
        }
    return None


def _match_okx_round_trip(
    inst_id: str,
    is_long: bool,
    window_start_ms: int,
    window_end_ms: int,
    fetch: Callable[..., list[dict]],
    credentials: dict[str, str],
) -> dict | None:
    """Find a closed OKX position for *inst_id* in the window.

    OKX `positions-history` rows already represent a full closed round trip
    (fields: `direction` "long"/"short", `openAvgPx`, `closeAvgPx`, `pnl`,
    `cTime` open, `uTime` close -- per OKX's documented positions-history schema).
    """
    wanted_direction = "long" if is_long else "short"
    rows = fetch(
        inst_id,
        before=str(window_start_ms),
        after="",
        api_key=credentials.get("api_key", ""),
        api_secret=credentials.get("api_secret", ""),
        passphrase=credentials.get("passphrase", ""),
    )
    for row in rows:
        if row.get("direction") != wanted_direction:
            continue
        c_time = int(row.get("cTime") or 0)
        u_time = int(row.get("uTime") or 0)
        if not (window_start_ms <= c_time <= window_end_ms):
            continue
        return {
            "actual_entry_price": float(row.get("openAvgPx") or 0.0),
            "actual_exit_price": float(row.get("closeAvgPx") or 0.0),
            "filled_at_ms": c_time,
            "closed_at_ms": u_time,
            "pnl_usd": float(row.get("pnl") or 0.0),
        }
    return None


def backfill_csv(
    csv_path: Path,
    kind: Literal["mt5", "okx"],
    *,
    mt5_fetch: Callable[[str, int, int], list[dict]] | None = None,
    okx_fetch: Callable[..., list[dict]] | None = None,
    okx_credentials: dict[str, str] | None = None,
    now: datetime | None = None,
) -> BackfillResult:
    """Back-fill unfilled rows of *csv_path* in place. Idempotent: rows whose
    `fill_status` is already non-empty are skipped, not re-queried."""
    if kind == "mt5":
        from pa_agent.data.trade_history import fetch_mt5_deals as _default_mt5_fetch
        fetch_mt5 = mt5_fetch or _default_mt5_fetch
    else:
        from pa_agent.data.trade_history import fetch_okx_positions_history as _default_okx_fetch
        fetch_okx = okx_fetch or _default_okx_fetch
        creds = okx_credentials or {}

    fieldnames, rows = _read_csv(csv_path)
    for col in FILL_COLUMNS:
        if col not in fieldnames:
            fieldnames.append(col)

    now = now or datetime.now(timezone.utc)
    processed = matched = unmatched = skipped = 0

    for i, row in enumerate(rows):
        if (row.get("fill_status") or "").strip():
            skipped += 1
            continue

        record_time_raw = row.get("record_time", "")
        if not record_time_raw:
            continue
        try:
            window_start = _parse_record_time(record_time_raw)
        except ValueError:
            logger.warning("Unparseable record_time %r in %s row %d", record_time_raw, csv_path, i)
            continue

        if i + 1 < len(rows) and rows[i + 1].get("record_time"):
            try:
                window_end = _parse_record_time(rows[i + 1]["record_time"])
            except ValueError:
                window_end = min(now, window_start + timedelta(days=_MAX_LOOKAHEAD_DAYS))
        else:
            window_end = min(now, window_start + timedelta(days=_MAX_LOOKAHEAD_DAYS))

        symbol = row.get("symbol", "")
        direction = row.get("order_direction", "")
        is_long = _is_long(direction)
        window_start_ms = int(window_start.timestamp() * 1000)
        window_end_ms = int(window_end.timestamp() * 1000)

        processed += 1
        match = None
        try:
            if kind == "mt5":
                match = _match_mt5_round_trip(symbol, is_long, window_start_ms, window_end_ms, fetch_mt5)
            else:
                match = _match_okx_round_trip(
                    symbol, is_long, window_start_ms, window_end_ms, fetch_okx, creds,
                )
        except DataSourceTransientError as exc:
            logger.warning("backfill lookup failed for %s row %d: %s", csv_path, i, exc)

        if match is None:
            row["fill_status"] = "unfilled"
            row["match_confidence"] = "unmatched"
            unmatched += 1
            continue

        entry_price = match["actual_entry_price"]
        exit_price = match["actual_exit_price"]
        pnl_usd = match["pnl_usd"]
        holding_s = max(0, (match["closed_at_ms"] - match["filled_at_ms"]) // 1000)
        pnl_pips = (exit_price - entry_price) if is_long else (entry_price - exit_price)

        row["fill_status"] = "filled"
        row["actual_entry_price"] = str(entry_price)
        row["actual_exit_price"] = str(exit_price)
        row["filled_at"] = datetime.fromtimestamp(match["filled_at_ms"] / 1000, tz=timezone.utc).isoformat()
        row["closed_at"] = datetime.fromtimestamp(match["closed_at_ms"] / 1000, tz=timezone.utc).isoformat()
        row["pnl_usd"] = str(pnl_usd)
        row["pnl_pips"] = str(pnl_pips)
        row["holding_duration_s"] = str(int(holding_s))
        row["win_loss"] = "win" if pnl_usd > 0 else ("loss" if pnl_usd < 0 else "breakeven")
        row["match_confidence"] = "matched"
        matched += 1

    _write_csv(csv_path, fieldnames, rows)
    return BackfillResult(
        processed=processed, matched=matched, unmatched=unmatched, skipped_already_filled=skipped,
    )
