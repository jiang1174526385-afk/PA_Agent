"""OKX public-market-data source (spot + perpetual swap).

Uses OKX's public REST endpoints only (``/api/v5/market/candles`` and
``/api/v5/public/instruments``) — no API key/secret/passphrase required,
since these are public market-data endpoints, not trading endpoints.

Symbol format follows OKX's native ``instId`` convention, e.g.
``BTC-USDT-SWAP`` (perpetual swap) or ``BTC-USDT`` (spot) — the same
convention used by this project's sibling trading-terminal codebase.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from pa_agent.data.base import (
    DataSource,
    DataSourceTransientError,
    KlineBar,
    normalize_kline_bar,
)

logger = logging.getLogger(__name__)

_BASE_URL = "https://www.okx.com"

# Our timeframe strings → OKX candle "bar" codes.
_TF_MAP: dict[str, str] = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1H",
    "2h": "2H",
    "4h": "4H",
    "6h": "6H",
    "12h": "12H",
    "1d": "1D",
    "1w": "1W",
    "1M": "1M",
}

_DEFAULT_SYMBOLS: tuple[str, ...] = (
    "BTC-USDT-SWAP",
    "ETH-USDT-SWAP",
    "SOL-USDT-SWAP",
    "BTC-USDT",
    "ETH-USDT",
)

_REQUEST_TIMEOUT_SEC = 10.0


def _http_get_json(path: str, params: dict[str, str]) -> dict:
    from urllib.parse import urlencode

    url = f"{_BASE_URL}{path}?{urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "pa-agent/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=_REQUEST_TIMEOUT_SEC) as resp:
            raw = resp.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        raise DataSourceTransientError(f"OKX request failed: {exc}") from exc

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise DataSourceTransientError(f"OKX returned invalid JSON: {exc}") from exc

    code = str(data.get("code", "0"))
    if code != "0":
        raise DataSourceTransientError(
            f"OKX error [{code}] {data.get('msg') or 'unknown error'}"
        )
    return data


class OKXSource(DataSource):
    """K-line data from OKX public market-data REST endpoints."""

    def __init__(self) -> None:
        self._symbol: str = ""
        self._timeframe: str = ""
        self._connected: bool = False

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def connect(self) -> None:
        # Public endpoints, nothing to authenticate — a lightweight reachability
        # probe is enough to fail fast on a dead network instead of at first fetch.
        try:
            _http_get_json("/api/v5/public/instruments", {"instType": "SWAP"})
        except DataSourceTransientError:
            raise
        self._connected = True
        logger.info("OKXSource connected")

    def disconnect(self) -> None:
        self._connected = False
        logger.info("OKXSource disconnected")

    # ── Discovery ─────────────────────────────────────────────────────────────

    def list_symbols(self) -> list[str]:
        try:
            data = _http_get_json("/api/v5/public/instruments", {"instType": "SWAP"})
        except DataSourceTransientError:
            return list(_DEFAULT_SYMBOLS)

        symbols = [
            row["instId"]
            for row in data.get("data", [])
            if row.get("state") == "live" and row.get("instId", "").endswith("-USDT-SWAP")
        ]
        return sorted(symbols) if symbols else list(_DEFAULT_SYMBOLS)

    def supported_timeframes(self) -> list[str]:
        return list(_TF_MAP.keys())

    # ── Subscription ──────────────────────────────────────────────────────────

    def subscribe(self, symbol: str, timeframe: str) -> None:
        if timeframe not in _TF_MAP:
            raise ValueError(
                f"Unsupported timeframe: {timeframe!r}. Use one of {list(_TF_MAP)}"
            )
        self._symbol = symbol
        self._timeframe = timeframe
        logger.info("OKXSource subscribed: %s %s", symbol, timeframe)

    def unsubscribe(self) -> None:
        self._symbol = ""
        self._timeframe = ""
        logger.info("OKXSource unsubscribed")

    # ── Data fetch ────────────────────────────────────────────────────────────

    def latest_snapshot(self, n: int) -> list[KlineBar]:
        """Return *n* bars newest-first; bars[0] is the forming (unclosed) bar."""
        if not self._connected:
            raise DataSourceTransientError("Not connected — call connect() first")
        if not self._symbol or not self._timeframe:
            raise DataSourceTransientError("Not subscribed — call subscribe() first")

        bar = _TF_MAP[self._timeframe]
        data = _http_get_json(
            "/api/v5/market/candles",
            {"instId": self._symbol, "bar": bar, "limit": str(min(n, 300))},
        )
        rows = data.get("data", [])
        if not rows:
            raise DataSourceTransientError(
                f"OKX returned no candles for {self._symbol} {bar}"
            )

        # OKX returns rows newest-first already:
        # [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
        bars: list[KlineBar] = []
        for i, row in enumerate(rows[:n]):
            ts_ms, o, h, low, c, vol = row[0], row[1], row[2], row[3], row[4], row[5]
            vol_ccy_quote = row[7] if len(row) > 7 else "0"
            confirm = row[8] if len(row) > 8 else "1"
            bars.append(
                normalize_kline_bar(
                    KlineBar(
                        seq=i + 1,
                        ts_open=float(ts_ms),
                        open=float(o),
                        high=float(h),
                        low=float(low),
                        close=float(c),
                        volume=float(vol),
                        amount=float(vol_ccy_quote or 0.0),
                        closed=(str(confirm) == "1"),
                    )
                )
            )
        return bars
