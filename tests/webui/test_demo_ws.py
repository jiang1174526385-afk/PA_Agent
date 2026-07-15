from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.webui.api import analysis as analysis_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner


def _write_record(directory, name: str) -> None:
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
        "stage1_messages": [
            {"role": "system", "content": "s1-system"},
            {"role": "user", "content": "s1-user"},
        ],
        "stage1_response": {"reasoning_content": "s1r", "content": '{"gate_result": "proceed"}'},
        "stage1_diagnosis": {"gate_result": "proceed"},
        "stage2_messages": [
            {"role": "system", "content": "s2-system"},
            {"role": "user", "content": "s2-user"},
        ],
        "stage2_response": {"reasoning_content": "s2r", "content": "{}"},
        "stage2_decision": {
            "decision": {
                "order_type": "限价单",
                "order_direction": "做多",
                "entry_price": 100.0,
                "trade_confidence": 90,
            },
        },
        "strategy_files_used": ["strategy_a.txt"],
        "experience_loaded": [],
        "exception": None,
        "usage_total": {},
    }
    (directory / name).write_text(json.dumps(payload), encoding="utf-8")


def _build_app(tmp_path, monkeypatch):
    records_dir = tmp_path / "records" / "pending"
    monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", records_dir)
    _write_record(records_dir, "demo1.json")

    app = FastAPI()
    app.include_router(analysis_api.ws_router)
    state = AppState(ctx=None, orchestrator=None, analysis_runner=AnalysisRunner(None))
    app.state.pa_state = state
    return app, state, records_dir


def _collect_until(ws, predicate, limit=500):
    messages = []
    for _ in range(limit):
        msg = ws.receive_json()
        messages.append(msg)
        if predicate(msg):
            return messages
    raise AssertionError(f"predicate never satisfied, got: {messages}")


def test_demo_replay_message_sequence(tmp_path, monkeypatch):
    app, _state, _records_dir = _build_app(tmp_path, monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "demo", "demo_record_id": "demo1.json"})
        messages = _collect_until(ws, lambda m: m["type"] == "demo_finished")

        types = [m["type"] for m in messages]
        assert "stage1_reasoning" in types
        assert "stage_prompt" in types
        assert "stage2_files" in types
        assert "stage2_reasoning" in types
        assert types.index("record") < types.index("demo_finished")
        record_msg = next(m for m in messages if m["type"] == "record")
        assert record_msg["record"]["meta"]["symbol"] == "FAKEUSD"
        assert messages[-1]["type"] == "demo_finished"


def test_demo_replay_missing_record_errors(tmp_path, monkeypatch):
    app, _state, _records_dir = _build_app(tmp_path, monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "demo", "demo_record_id": "does-not-exist.json"})
        msg = ws.receive_json()
        assert msg == {"type": "error", "message": "演示记录不存在"}


def test_demo_replay_rejects_path_traversal(tmp_path, monkeypatch):
    app, _state, records_dir = _build_app(tmp_path, monkeypatch)
    # A file that exists, but outside RECORDS_PENDING_DIR.
    outside = records_dir.parent.parent / "secret.json"
    outside.write_text("{}", encoding="utf-8")

    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json(
            {"type": "submit", "mode": "demo", "demo_record_id": "../../secret.json"}
        )
        msg = ws.receive_json()
        assert msg == {"type": "error", "message": "演示记录不存在"}


def test_demo_replay_rejects_second_submit_while_busy(tmp_path, monkeypatch):
    app, _state, _records_dir = _build_app(tmp_path, monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "demo", "demo_record_id": "demo1.json"})
        ws.send_json({"type": "submit", "mode": "demo", "demo_record_id": "demo1.json"})
        messages = _collect_until(ws, lambda m: m["type"] == "error")
        assert messages[-1] == {"type": "error", "message": "分析进行中"}
        _collect_until(ws, lambda m: m["type"] == "demo_finished")


def test_demo_replay_cancel_stops_before_record(tmp_path, monkeypatch):
    app, _state, _records_dir = _build_app(tmp_path, monkeypatch)
    with TestClient(app) as client, client.websocket_connect("/ws/analysis") as ws:
        ws.send_json({"type": "submit", "mode": "demo", "demo_record_id": "demo1.json"})
        ws.send_json({"type": "cancel"})
        messages = _collect_until(
            ws, lambda m: m["type"] == "event" and m.get("event") == "DemoCancelled"
        )
        assert not any(m["type"] == "record" for m in messages)
