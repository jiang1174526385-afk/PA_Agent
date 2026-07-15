"""Phase-6 "demo replay + order-opportunity notify" browser e2e smoke suite.

Reuses the shared `live_server` fixture (real uvicorn + real
`AppContext.bootstrap()`; feishu/pushplus stay unconfigured in the e2e tmp
settings.json, so `send_order_signal()` short-circuits before any network
call -- see pa_agent/notify/feishu_notifier.py::send_order_signal's
`webhook_url` guard).
"""

from __future__ import annotations

import json

import pytest

from pa_agent.records.schema import AnalysisRecord, RecordMeta


def _write_demo_record(records_dir, name: str) -> None:
    records_dir.mkdir(parents=True, exist_ok=True)
    meta = RecordMeta(
        timestamp_local_iso="2026-07-15T00:00:00",
        timestamp_local_ms=0,
        symbol="BTC-USDT-SWAP",
        timeframe="15m",
        bar_count=1,
        ai_provider={"model": "e2e-demo"},
    )
    record = AnalysisRecord(
        meta=meta,
        kline_data=[],
        htf_text="",
        stage1_messages=[
            {"role": "system", "content": "[e2e demo] stage1 system prompt"},
            {"role": "user", "content": "[e2e demo] stage1 user prompt"},
        ],
        stage1_response={
            "reasoning_content": "[e2e demo] 阶段一思考…\n",
            "content": '{"gate_result": "proceed"}',
        },
        stage1_diagnosis={"gate_result": "proceed", "direction": "上涨"},
        stage2_messages=[
            {"role": "system", "content": "[e2e demo] stage2 system prompt"},
            {"role": "user", "content": "[e2e demo] stage2 user prompt"},
        ],
        stage2_response={
            "reasoning_content": "[e2e demo] 阶段二思考…\n",
            "content": "{}",
        },
        # Flat shape (order_type at top level) -- matches this webui test
        # suite's established fixture convention (see conftest.py::_build_record).
        stage2_decision={
            "order_type": "限价单",
            "order_direction": "做多",
            "entry_price": 100.0,
            "trade_confidence": 90,
        },
        strategy_files_used=["e2e_demo_strategy.txt"],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )
    (records_dir / name).write_text(json.dumps(record.model_dump()), encoding="utf-8")


@pytest.mark.e2e
def test_demo_replay_shows_streamed_decision_and_order_alert(live_server, page):
    console_errors = []
    page.on(
        "console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None
    )
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _write_demo_record(live_server["records_dir"], "demo_e2e.json")

    page.goto(live_server["base_url"])
    page.wait_for_selector("[data-testid='demo-record-select']", timeout=15_000)
    page.wait_for_function(
        "document.querySelector('[data-testid=\"demo-record-select\"]').options.length > 1",
        timeout=15_000,
    )
    page.get_by_test_id("demo-record-select").select_option(value="demo_e2e.json")
    page.get_by_test_id("demo-play-button").click()

    # Streamed reasoning + final decision from the replayed record.
    page.wait_for_selector("text=限价单", timeout=15_000)
    # Order-opportunity toast (page-in toast only -- no browser Notification API,
    # no sound; confirmed with the user in phase-6-execution-plan.md §0.2).
    page.wait_for_selector("[data-testid='order-opportunity-toast']", timeout=15_000)
    page.get_by_test_id("order-opportunity-toast").get_by_role("button", name="关闭").click()
    page.wait_for_selector("[data-testid='order-opportunity-toast']", state="detached", timeout=5_000)

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_demo_random_button_plays_when_only_one_record_available(live_server, page):
    _write_demo_record(live_server["records_dir"], "demo_random.json")

    page.goto(live_server["base_url"])
    page.wait_for_selector("[data-testid='demo-random-button']:not([disabled])", timeout=15_000)
    page.get_by_test_id("demo-random-button").click()

    page.wait_for_selector("text=限价单", timeout=15_000)
