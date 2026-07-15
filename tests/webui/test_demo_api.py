from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.webui.api import demo as demo_api


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(demo_api.router, prefix="/api")
    return TestClient(app)


def _write_record(directory, name: str, *, playable: bool) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "meta": {
            "timestamp_local_iso": "2026-07-15T00:00:00",
            "timestamp_local_ms": 0,
            "symbol": "FAKEUSD",
            "timeframe": "15m",
            "bar_count": 1,
            "ai_provider": {"model": "fake"},
            "decision_stance": "conservative",
        },
        "kline_data": [],
        "htf_text": "",
        "stage1_messages": [],
        "stage1_response": None,
        "stage1_diagnosis": {"gate_result": "proceed"} if playable else None,
        "stage2_messages": [],
        "stage2_response": None,
        "stage2_decision": None,
        "strategy_files_used": [],
        "experience_loaded": [],
        "exception": None,
        "usage_total": {},
    }
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def test_list_demo_records_filters_unplayable_and_broken(tmp_path, monkeypatch):
    records_dir = tmp_path / "records" / "pending"
    monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", records_dir)
    monkeypatch.setattr("pa_agent.demo.record_loader.RECORDS_PENDING_DIR", records_dir)

    _write_record(records_dir, "playable.json", playable=True)
    _write_record(records_dir, "unplayable.json", playable=False)
    (records_dir / "broken.json").write_text("{not json", encoding="utf-8")

    resp = _client().get("/api/demo/records")
    assert resp.status_code == 200
    body = resp.json()
    assert [r["record_id"] for r in body["records"]] == ["playable.json"]
    assert body["records"][0]["symbol"] == "FAKEUSD"
    assert body["records"][0]["timeframe"] == "15m"


def test_list_demo_records_empty_when_directory_missing(tmp_path, monkeypatch):
    records_dir = tmp_path / "does-not-exist"
    monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", records_dir)
    monkeypatch.setattr("pa_agent.demo.record_loader.RECORDS_PENDING_DIR", records_dir)

    resp = _client().get("/api/demo/records")
    assert resp.status_code == 200
    assert resp.json() == {"records": []}
