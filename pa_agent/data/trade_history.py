"""Real historical-fill lookups for the trade-record backfill (phase 2 web UI).

Two read-only functions, one per broker/exchange. Neither places, amends, nor
cancels anything -- they only look up deals/positions that already happened.

MT5 side uses the standard `MetaTrader5.history_deals_get()` API (already a
dependency of `pa_agent/data/mt5.py`; requires the MT5 terminal to be open and
`mt5.initialize()` to have already succeeded via `MT5Source.connect()`).

OKX side needs the *private* `/api/v5/account/positions-history` endpoint
(closed positions only), which requires HMAC-SHA256 request signing -- unlike
`pa_agent/data/okx_source.py`, which only calls public market-data endpoints.
The signing scheme below mirrors `tradingAgents/webui/terminal/okx_rest.py`
(`OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE` headers), rewritten with `urllib`
(synchronous) instead of `httpx`/`asyncio` to match this project's existing
`okx_source.py` HTTP style rather than pulling in a new async HTTP dependency.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime, timezone

from pa_agent.data.base import DataSourceTransientError

logger = logging.getLogger(__name__)

_OKX_BASE_URL = "https://www.okx.com"
_REQUEST_TIMEOUT_SEC = 10.0


# ── MT5 ───────────────────────────────────────────────────────────────────────

def fetch_mt5_deals(symbol: str, ts_from_ms: int, ts_to_ms: int) -> list[dict]:
    """Return closed deals for *symbol* in [ts_from_ms, ts_to_ms], oldest-first.

    Requires an already-`mt5.initialize()`d terminal (i.e. `MT5Source.connect()`
    must have been called first in this process). Returns MT5's native deal
    fields unchanged (`ticket`, `order`, `time`, `time_msc`, `type`, `entry`,
    `price`, `volume`, `profit`, `symbol`, `comment`, ...) -- see
    `pa_agent/docs/webui_migration/phase-2-execution-plan.md` §5.2 for why we
    don't rename them to OKX's convention here.
    """
    try:
        import MetaTrader5 as mt5  # type: ignore[import]
    except ImportError as exc:
        raise DataSourceTransientError(
            "MetaTrader5 package not installed — run: pip install MetaTrader5"
        ) from exc

    date_from = datetime.fromtimestamp(ts_from_ms / 1000, tz=timezone.utc)
    date_to = datetime.fromtimestamp(ts_to_ms / 1000, tz=timezone.utc)

    deals = mt5.history_deals_get(date_from, date_to, group=symbol)
    if deals is None:
        error = mt5.last_error()
        # last_error() == (1, 'Success') means "no deals found", not a failure.
        if error and error[0] not in (1, 0):
            raise DataSourceTransientError(f"MT5 history_deals_get failed: {error}")
        return []

    return [deal._asdict() for deal in deals]


# ── OKX ───────────────────────────────────────────────────────────────────────

def _okx_ts() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _okx_sign(ts: str, method: str, path: str, body: str, api_secret: str) -> str:
    msg = ts + method.upper() + path + body
    raw = hmac.new(api_secret.encode(), msg.encode(), hashlib.sha256).digest()
    return base64.b64encode(raw).decode()


def _okx_headers(
    method: str, path: str, api_key: str, api_secret: str, passphrase: str, body: str = "",
) -> dict[str, str]:
    ts = _okx_ts()
    return {
        "OK-ACCESS-KEY": api_key,
        "OK-ACCESS-SIGN": _okx_sign(ts, method, path, body, api_secret),
        "OK-ACCESS-TIMESTAMP": ts,
        "OK-ACCESS-PASSPHRASE": passphrase,
        "Content-Type": "application/json",
    }


def fetch_okx_positions_history(
    inst_id: str,
    after: str = "",
    before: str = "",
    *,
    api_key: str,
    api_secret: str,
    passphrase: str,
    limit: int = 100,
) -> list[dict]:
    """Return closed positions for *inst_id* from OKX's private history endpoint.

    `after`/`before` are OKX `uTime` cursor strings (milliseconds), matching
    `get_positions_history()` semantics in `tradingAgents/webui/terminal/okx_rest.py`.
    Raises `DataSourceTransientError` if credentials are missing/rejected or the
    request fails, matching this project's own `okx_source.py` error convention
    (rather than surfacing a raw `OKXError`, which only exists in the sibling
    `tradingAgents` codebase).
    """
    if not (api_key and api_secret and passphrase):
        raise DataSourceTransientError(
            "OKX API Key/Secret/Passphrase 未配置 — 请在设置的 OKX 分区填写"
        )

    from urllib.parse import urlencode

    params: dict[str, str] = {"instType": "SWAP", "limit": str(limit)}
    if inst_id:
        params["instId"] = inst_id
    if after:
        params["after"] = after
    if before:
        params["before"] = before

    path = "/api/v5/account/positions-history"
    full_path = path + "?" + urlencode(params)
    headers = _okx_headers("GET", full_path, api_key, api_secret, passphrase)

    req = urllib.request.Request(
        _OKX_BASE_URL + full_path, headers=headers, method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DataSourceTransientError(f"OKX positions-history request failed: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataSourceTransientError(f"OKX returned invalid JSON: {exc}") from exc

    code = str(data.get("code", "0"))
    if code != "0":
        raise DataSourceTransientError(
            f"OKX error [{code}] {data.get('msg') or 'unknown error'}"
        )
    return data.get("data", [])
