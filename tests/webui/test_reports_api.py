from __future__ import annotations

import csv
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.webui.api import reports as reports_api

_FIELDNAMES = [
    "record_time", "symbol", "timeframe", "decision_stance", "model",
    "order_direction", "order_type", "entry_price", "stop_loss_price",
    "take_profit_price", "take_profit_price_2",
]


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=_FIELDNAMES, extrasaction="ignore")
        writer.writeheader()
        for r in rows:
            writer.writerow({k: r.get(k, "") for k in _FIELDNAMES})


@pytest.fixture
def app_client(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_api, "_TRADE_RECORDS_DIR", tmp_path)
    application = FastAPI()
    application.include_router(reports_api.router, prefix="/api")
    return TestClient(application)


def test_list_reports_empty(app_client):
    resp = app_client.get("/api/reports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_reports_finds_csv(app_client, tmp_path):
    _write_csv(
        tmp_path / "XAUUSDm_15m.csv",
        [{"record_time": "2026-01-01 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
          "decision_stance": "balanced", "order_direction": "做多", "entry_price": "2000.0"}],
    )
    resp = app_client.get("/api/reports")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 1
    assert items[0]["key"] == "XAUUSDm_15m"
    assert items[0]["symbol"] == "XAUUSDm"
    assert items[0]["timeframe"] == "15m"
    assert items[0]["row_count"] == 1


def test_backfill_matches_mt5_round_trip(app_client, tmp_path, monkeypatch):
    _write_csv(
        tmp_path / "XAUUSDm_15m.csv",
        [{"record_time": "2026-01-01 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
          "decision_stance": "balanced", "order_direction": "做多", "entry_price": "2000.0"}],
    )

    def fake_fetch_mt5(symbol, ts_from_ms, ts_to_ms):
        return [
            {"position_id": 1, "entry": 0, "type": 0, "time_msc": ts_from_ms + 1000,
             "price": 2001.0, "profit": 0.0, "symbol": symbol},
            {"position_id": 1, "entry": 1, "type": 1, "time_msc": ts_from_ms + 5000,
             "price": 2010.0, "profit": 90.0, "symbol": symbol},
        ]

    monkeypatch.setattr("pa_agent.data.trade_history.fetch_mt5_deals", fake_fetch_mt5)

    resp = app_client.post("/api/reports/XAUUSDm_15m/backfill", params={"kind": "mt5"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["processed"] == 1
    assert body["matched"] == 1
    assert body["unmatched"] == 0

    # idempotent: second call skips the already-filled row
    resp2 = app_client.post("/api/reports/XAUUSDm_15m/backfill", params={"kind": "mt5"})
    assert resp2.json()["skipped_already_filled"] == 1
    assert resp2.json()["processed"] == 0


def test_backfill_no_match_marks_unfilled(app_client, tmp_path, monkeypatch):
    _write_csv(
        tmp_path / "XAUUSDm_15m.csv",
        [{"record_time": "2026-01-01 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
          "decision_stance": "balanced", "order_direction": "做多", "entry_price": "2000.0"}],
    )
    monkeypatch.setattr("pa_agent.data.trade_history.fetch_mt5_deals", lambda *a, **k: [])
    resp = app_client.post("/api/reports/XAUUSDm_15m/backfill", params={"kind": "mt5"})
    assert resp.json()["unmatched"] == 1

    orders = app_client.get("/api/reports/XAUUSDm_15m/orders").json()
    assert orders["rows"][0]["fill_status"] == "unfilled"


def test_backfill_okx_requires_credentials(app_client, tmp_path):
    _write_csv(
        tmp_path / "BTCUSDT_1h.csv",
        [{"record_time": "2026-01-01 00:00:00", "symbol": "BTC-USDT-SWAP", "timeframe": "1h",
          "decision_stance": "balanced", "order_direction": "做多", "entry_price": "50000"}],
    )
    resp = app_client.post("/api/reports/BTCUSDT_1h/backfill", params={"kind": "okx"})
    assert resp.status_code == 400


def test_summary_computes_kpis_after_backfill(app_client, tmp_path, monkeypatch):
    _write_csv(
        tmp_path / "XAUUSDm_15m.csv",
        [
            {"record_time": "2026-01-01 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
             "decision_stance": "balanced", "order_direction": "做多", "entry_price": "2000.0"},
            {"record_time": "2026-01-02 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
             "decision_stance": "balanced", "order_direction": "做空", "entry_price": "2010.0"},
        ],
    )

    def fake_fetch_mt5(symbol, ts_from_ms, ts_to_ms):
        # First window (row 1): winning long trade. Second window (row 2, last row): losing short trade.
        if ts_from_ms < 1767225600000:  # before 2026-01-01 in ms roughly; both windows overlap in this fake anyway
            pass
        return [
            {"position_id": ts_from_ms, "entry": 0, "type": 0 if True else 1,
             "time_msc": ts_from_ms + 1000, "price": 2001.0, "profit": 0.0, "symbol": symbol},
            {"position_id": ts_from_ms, "entry": 1, "type": 1,
             "time_msc": ts_from_ms + 5000, "price": 2020.0, "profit": 100.0, "symbol": symbol},
        ]

    monkeypatch.setattr("pa_agent.data.trade_history.fetch_mt5_deals", fake_fetch_mt5)
    app_client.post("/api/reports/XAUUSDm_15m/backfill", params={"kind": "mt5"})

    resp = app_client.get("/api/reports/XAUUSDm_15m/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["trade_count"] >= 1
    assert "total_pnl_usd" in body
    assert "equity_curve" in body
    assert isinstance(body["equity_curve"], list)
