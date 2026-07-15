from __future__ import annotations

import time

import pytest

from pa_agent.data.base import DataSource, KlineBar


class FakeDataSource(DataSource):
    """Deterministic in-memory `DataSource` for webui tests (no network/MT5)."""

    def __init__(self, symbols=("FAKEUSD",), timeframes=("15m",), n_available=200):
        self._symbols = list(symbols)
        self._timeframes = list(timeframes)
        self._n_available = n_available
        self._connected = False
        self._symbol = None
        self._timeframe = None
        self.connect_calls = 0
        self.disconnect_calls = 0

    def connect(self) -> None:
        self._connected = True
        self.connect_calls += 1

    def disconnect(self) -> None:
        self._connected = False
        self.disconnect_calls += 1

    def list_symbols(self) -> list[str]:
        return list(self._symbols)

    def supported_timeframes(self) -> list[str]:
        return list(self._timeframes)

    def subscribe(self, symbol: str, timeframe: str) -> None:
        self._symbol = symbol
        self._timeframe = timeframe

    def unsubscribe(self) -> None:
        self._symbol = None
        self._timeframe = None

    def latest_snapshot(self, n: int) -> list[KlineBar]:
        n = min(n, self._n_available)
        now_ms = int(time.time() * 1000)
        bar_s = 15 * 60
        bars = []
        base_price = 100.0
        for i in range(n):
            ts_open = now_ms - (i + 5) * bar_s * 1000
            price = base_price + (n - i) * 0.1
            bars.append(
                KlineBar(
                    seq=i + 1,
                    ts_open=float(ts_open),
                    open=price,
                    high=price + 0.5,
                    low=price - 0.5,
                    close=price + 0.2,
                    volume=1000.0 + i,
                    closed=True,
                )
            )
        return bars


@pytest.fixture
def fake_data_source() -> FakeDataSource:
    return FakeDataSource()
