"""Unit tests for the OKX data source (no network — HTTP layer is monkeypatched)."""
from __future__ import annotations

import pytest

from pa_agent.data import okx_source
from pa_agent.data.base import DataSourceTransientError
from pa_agent.data.okx_source import OKXSource


def test_supported_timeframes_include_native_bar_codes():
    src = OKXSource()
    assert "1h" in src.supported_timeframes()
    assert "4h" in src.supported_timeframes()
    assert "1d" in src.supported_timeframes()


def test_subscribe_rejects_unsupported_timeframe():
    src = OKXSource()
    with pytest.raises(ValueError):
        src.subscribe("BTC-USDT-SWAP", "7m")


def test_latest_snapshot_requires_connect_and_subscribe():
    src = OKXSource()
    with pytest.raises(DataSourceTransientError):
        src.latest_snapshot(10)

    src._connected = True
    with pytest.raises(DataSourceTransientError):
        src.latest_snapshot(10)


def test_connect_probes_instruments_endpoint(monkeypatch):
    calls = []

    def fake_get(path, params):
        calls.append((path, params))
        return {"code": "0", "data": []}

    monkeypatch.setattr(okx_source, "_http_get_json", fake_get)
    src = OKXSource()
    src.connect()
    assert src._connected is True
    assert calls[0][0] == "/api/v5/public/instruments"


def test_latest_snapshot_parses_candles_newest_first(monkeypatch):
    # OKX candle row: [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    rows = [
        ["1700000300000", "101", "102", "100", "101.5", "5", "5", "505", "0"],  # forming
        ["1700000000000", "100", "103", "99", "101", "10", "10", "1010", "1"],  # closed
    ]

    def fake_get(path, params):
        assert path == "/api/v5/market/candles"
        assert params["instId"] == "BTC-USDT-SWAP"
        assert params["bar"] == "4H"
        return {"code": "0", "data": rows}

    monkeypatch.setattr(okx_source, "_http_get_json", fake_get)
    src = OKXSource()
    src._connected = True
    src.subscribe("BTC-USDT-SWAP", "4h")

    bars = src.latest_snapshot(2)
    assert len(bars) == 2
    assert bars[0].seq == 1
    assert bars[0].closed is False
    assert bars[0].close == 101.5
    assert bars[1].seq == 2
    assert bars[1].closed is True
    assert bars[1].amount == 1010.0


def test_latest_snapshot_raises_on_empty_candles(monkeypatch):
    monkeypatch.setattr(okx_source, "_http_get_json", lambda path, params: {"code": "0", "data": []})
    src = OKXSource()
    src._connected = True
    src.subscribe("BTC-USDT-SWAP", "1h")
    with pytest.raises(DataSourceTransientError):
        src.latest_snapshot(10)


def test_list_symbols_falls_back_on_transient_error(monkeypatch):
    def fake_get(path, params):
        raise DataSourceTransientError("network down")

    monkeypatch.setattr(okx_source, "_http_get_json", fake_get)
    src = OKXSource()
    symbols = src.list_symbols()
    assert "BTC-USDT-SWAP" in symbols
