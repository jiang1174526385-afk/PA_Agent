from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.webui.api import kline as kline_api
from pa_agent.webui.deps import AppState
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
