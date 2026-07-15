from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient

from pa_agent.webui.api import decision_tree as decision_tree_api


def _client() -> TestClient:
    app = FastAPI()
    app.include_router(decision_tree_api.router, prefix="/api")
    return TestClient(app)


def test_static_tree_matches_load_decision_tree():
    from pa_agent.ai.decision_tree import load_decision_tree

    expected = load_decision_tree()
    resp = _client().get("/api/decision-tree/static")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == expected["version"]
    assert body["source"] == expected["source"]
    assert len(body["sections"]) == len(expected["sections"])
    assert body["sections"][0]["nodes"][0]["id"] == expected["sections"][0]["nodes"][0]["id"]


def test_replay_merges_gate_and_decision_trace_with_terminal():
    gate_trace = [
        {
            "node_id": "1.1",
            "question": "问题1（基于K10-K1判断）",
            "answer": "是",
            "reason": "理由1",
            "bar_range": "K10-K1",
        },
    ]
    decision_trace = [
        {
            "node_id": "9.0",
            "question": "问题2",
            "answer": "否",
            "reason": "理由2",
            "bar_range": "K3-K1",
            "branch": "no",
        },
    ]
    terminal = {"node_id": "9.0", "outcome": "wait", "label": "等待更清晰信号"}

    resp = _client().post(
        "/api/decision-tree/replay",
        json={
            "gate_trace": gate_trace,
            "decision_trace": decision_trace,
            "terminal": terminal,
            "gate_result": "proceed",
            "gate_shortcircuited": False,
        },
    )
    assert resp.status_code == 200
    body = resp.json()

    assert [r["node_id"] for r in body["rows"]] == ["1.1", "9.0"]
    assert body["rows"][0]["phase"] == "gate"
    assert body["rows"][0]["phase_zh"] == "闸门"
    assert body["rows"][0]["answer_display"] == "是"
    assert body["rows"][0]["answer_color_key"] == "success"
    assert body["rows"][1]["phase"] == "decision"
    assert body["rows"][1]["answer_color_key"] == "danger"
    assert body["visited_ids"] == ["1.1", "9.0"]
    assert body["terminal_banner"]["color_key"] == "warning"
    assert "9.0" in body["terminal_banner"]["text"]
    assert body["gate_hint"] == "阶段一 gate_result：proceed"


def test_replay_gate_shortcircuited_no_terminal():
    gate_trace = [
        {
            "node_id": "1.3",
            "question": "闸门问题",
            "answer": "否",
            "reason": "闸门未通过",
            "bar_range": "K5-K1",
        },
    ]
    resp = _client().post(
        "/api/decision-tree/replay",
        json={
            "gate_trace": gate_trace,
            "decision_trace": [],
            "terminal": None,
            "gate_result": "wait",
            "gate_shortcircuited": True,
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["terminal_banner"]["color_key"] == "warning"
    assert "阶段一闸门" in body["terminal_banner"]["text"]
    assert "非模型策略评估" in body["gate_hint"]


def test_replay_empty_traces_returns_no_terminal_info():
    resp = _client().post("/api/decision-tree/replay", json={})
    assert resp.status_code == 200
    body = resp.json()
    assert body["rows"] == []
    assert body["visited_ids"] == []
    assert body["terminal_banner"]["color_key"] == "muted"
    assert body["gate_hint"] == ""
