from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.data.base import IndicatorBundle, KlineBar, KlineFrame
from pa_agent.webui.api import kline as kline_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.schemas.kline import KlineFrameOut
from tests.webui.conftest import FakeDataSource


@pytest.fixture
def app(monkeypatch):
    monkeypatch.setattr(kline_api, "create_data_source", lambda kind: FakeDataSource())
    application = FastAPI()
    application.include_router(kline_api.router, prefix="/api")
    application.include_router(kline_api.ws_router)
    application.state.pa_state = AppState(ctx=None, orchestrator=None, analysis_runner=None)
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as c:
        yield c


def test_list_data_sources(client):
    resp = client.get("/api/data-sources")
    assert resp.status_code == 200
    kinds = [item["kind"] for item in resp.json()]
    assert "mt5" in kinds and "tradingview" in kinds and "okx" in kinds


def test_list_symbols_connects_and_disconnects(client, monkeypatch):
    created: list[FakeDataSource] = []

    def factory(kind):
        ds = FakeDataSource(symbols=("ABCUSD", "XYZUSD"))
        created.append(ds)
        return ds

    monkeypatch.setattr(kline_api, "create_data_source", factory)

    resp = client.get("/api/data-sources/okx/symbols")
    assert resp.status_code == 200
    assert resp.json()["symbols"] == ["ABCUSD", "XYZUSD"]
    assert created[0].connect_calls == 1
    assert created[0].disconnect_calls == 1


def test_list_timeframes(client):
    resp = client.get("/api/data-sources/okx/timeframes")
    assert resp.status_code == 200
    assert "15m" in resp.json()["timeframes"]


def test_kline_snapshot_returns_frame(client):
    resp = client.get(
        "/api/kline/snapshot",
        params={"source": "okx", "symbol": "FAKEUSD", "timeframe": "15m", "n": 60},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["symbol"] == "FAKEUSD"
    assert body["timeframe"] == "15m"
    assert len(body["bars"]) == 60
    assert len(body["indicators"]["ema20"]) == 60


def test_kline_snapshot_insufficient_bars_422(client, monkeypatch):
    monkeypatch.setattr(kline_api, "create_data_source", lambda kind: FakeDataSource(n_available=5))
    resp = client.get(
        "/api/kline/snapshot",
        params={"source": "okx", "symbol": "FAKEUSD", "timeframe": "15m", "n": 60},
    )
    assert resp.status_code == 422


def _make_frame(*, forming: bool, ts_open_ms: float) -> KlineFrame:
    # bars[0] is newest-first (see pa_agent.data.base.KlineFrame docstring).
    forming_bar = KlineBar(
        seq=0 if forming else 1,
        ts_open=ts_open_ms,
        open=1.0,
        high=1.5,
        low=0.5,
        close=1.2,
        volume=10.0,
        closed=not forming,
    )
    older_bar = KlineBar(
        seq=1 if forming else 2,
        ts_open=ts_open_ms - 15 * 60 * 1000,
        open=1.0,
        high=1.5,
        low=0.5,
        close=1.2,
        volume=10.0,
        closed=True,
    )
    return KlineFrame(
        symbol="FAKEUSD",
        timeframe="15m",
        bars=(forming_bar, older_bar),
        indicators=IndicatorBundle(ema20=(1.1, 1.1), atr14=(0.2, 0.2)),
        snapshot_ts_local_ms=int(time.time() * 1000),
    )


def test_kline_frame_out_marks_forming_bar_with_positive_countdown():
    now_ms = int(time.time() * 1000)
    # Bar opened 5 minutes ago on a 15m timeframe -> still forming, ~10 min left.
    frame = _make_frame(forming=True, ts_open_ms=now_ms - 5 * 60 * 1000)

    out = KlineFrameOut.from_frame(frame)

    assert out.is_forming is True
    assert out.seconds_until_close is not None
    assert 0 < out.seconds_until_close <= 15 * 60


def test_kline_frame_out_closed_head_bar_has_no_countdown():
    now_ms = int(time.time() * 1000)
    frame = _make_frame(forming=False, ts_open_ms=now_ms - 20 * 60 * 1000)

    out = KlineFrameOut.from_frame(frame)

    assert out.is_forming is False
    assert out.seconds_until_close is None


def test_ws_kline_subscribe_and_receive_frame(client):
    with client.websocket_connect("/ws/kline") as ws:
        ws.send_json(
            {
                "type": "subscribe",
                "source": "okx",
                "symbol": "FAKEUSD",
                "timeframe": "15m",
                "n_bars": 60,
                "interval_ms": 50,
            }
        )
        subscribed = ws.receive_json()
        assert subscribed["type"] == "subscribed"
        epoch = subscribed["epoch"]

        frame_msg = ws.receive_json()
        assert frame_msg["type"] == "frame"
        assert frame_msg["epoch"] == epoch
        assert frame_msg["frame"]["symbol"] == "FAKEUSD"
        assert len(frame_msg["frame"]["bars"]) == 60


def test_ws_kline_resubscribe_bumps_epoch_and_tears_down_old_key(client):
    with client.websocket_connect("/ws/kline") as ws:
        ws.send_json(
            {
                "type": "subscribe",
                "source": "okx",
                "symbol": "AAA",
                "timeframe": "15m",
                "n_bars": 60,
                "interval_ms": 50,
            }
        )
        first = ws.receive_json()
        ws.receive_json()  # first frame

        ws.send_json(
            {
                "type": "subscribe",
                "source": "okx",
                "symbol": "BBB",
                "timeframe": "15m",
                "n_bars": 60,
                "interval_ms": 50,
            }
        )
        second = ws.receive_json()
        assert second["epoch"] > first["epoch"]

        frame_msg = ws.receive_json()
        assert frame_msg["frame"]["symbol"] == "BBB"
