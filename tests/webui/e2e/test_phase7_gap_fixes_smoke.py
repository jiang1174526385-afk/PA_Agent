"""Phase-7 browser e2e smoke suite for the gap-closing work done in this phase:

- "等待K线收盘后分析": checkbox arms a pending submit and shows a countdown;
  unchecking cancels it (mirrors PA_Agent使用文档.md §6).
- Chart freeze/resume: submitting an analysis freezes the chart on the
  snapshot at submit time; "图表实时更新" resumes live updates (§2/§4/§16).
- §0.1 fix + trader-equation display: a demo record whose `stage2_decision`
  uses the real (nested) `{"decision": {...}}` shape still renders order
  fields correctly, and the new 风险回报比/预估胜率/交易者方程 fields show up
  (PA_Agent使用文档.md §9).

Reuses the shared `live_server` fixture (real uvicorn + real OKX network data
source for the chart-freeze test; demo replay for the trader-equation test,
which needs no network and is fully deterministic).
"""

from __future__ import annotations

import json

import pytest

from pa_agent.records.schema import AnalysisRecord, RecordMeta


def _write_demo_record_nested(records_dir, name: str) -> None:
    """Write a demo record using the real (nested) stage2_decision shape --
    unlike this suite's usual flat-fixture convention -- so the e2e run
    exercises the §0.1 unwrap fix end-to-end, not just in isolation."""
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
        stage2_decision={
            "decision": {
                "order_type": "限价单",
                "order_direction": "做多",
                "entry_price": 100.0,
                "stop_loss_price": 95.0,
                "take_profit_price": 110.0,
                "take_profit_price_2": 115.0,
                "trade_confidence": 88,
                "estimated_win_rate": 65,
            },
            "decision_trace": [],
        },
        strategy_files_used=["e2e_demo_strategy.txt"],
        experience_loaded=[],
        exception=None,
        usage_total={},
    )
    (records_dir / name).write_text(json.dumps(record.model_dump()), encoding="utf-8")


@pytest.mark.e2e
def test_demo_replay_nested_decision_shows_order_fields_and_trader_equation(live_server, page):
    console_errors = []
    page.on(
        "console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None
    )
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _write_demo_record_nested(live_server["records_dir"], "demo_nested_e2e.json")

    page.goto(live_server["base_url"])
    page.wait_for_selector("[data-testid='demo-record-select']", timeout=15_000)
    page.wait_for_function(
        "document.querySelector('[data-testid=\"demo-record-select\"]').options.length > 1",
        timeout=15_000,
    )
    page.get_by_test_id("demo-record-select").select_option(value="demo_nested_e2e.json")
    page.get_by_test_id("demo-play-button").click()

    # Nested stage2_decision.decision.order_type must still render (§0.1 fix).
    page.wait_for_selector("text=限价单", timeout=15_000)

    # entry=100, sl=95, tp1=110, long => risk=5, reward=10, ratio=2.0:1;
    # win_rate=65% passes the trader equation (0.65*10 > 0.35*5).
    page.wait_for_selector("text=2.00 : 1", timeout=15_000)
    page.wait_for_selector("text=65%", timeout=5_000)
    page.wait_for_selector("text=通过", timeout=5_000)

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_chart_freezes_on_submit_and_resume_button_restores_live_updates(live_server, page):
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("BTC-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)

    assert page.get_by_test_id("resume-chart-button").count() == 0

    page.get_by_role("button", name="提交分析").click()
    # Freezing happens synchronously with submit, before the fake orchestrator
    # even returns -- the resume button should appear immediately.
    page.wait_for_selector("[data-testid='resume-chart-button']", timeout=5_000)

    page.wait_for_selector("text=买入", timeout=15_000)
    # Frozen chart persists after the analysis result arrives.
    assert page.get_by_test_id("resume-chart-button").count() == 1

    page.get_by_test_id("resume-chart-button").click()
    page.wait_for_selector("[data-testid='resume-chart-button']", state="detached", timeout=5_000)


@pytest.mark.e2e
def test_wait_for_close_checkbox_arms_countdown_and_uncheck_cancels(live_server, page):
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("ETH-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)

    page.get_by_label("等待收盘", exact=False).check()
    page.get_by_role("button", name="提交分析").click()

    # A 15m OKX bar is forming at essentially any wall-clock moment, so the
    # submit should be deferred and a countdown shown rather than starting
    # the analysis immediately (no "取消分析" button yet).
    page.wait_for_selector("[data-testid='wait-close-countdown']", timeout=5_000)
    assert page.get_by_role("button", name="取消分析").count() == 0

    # Desktop behaviour (PA_Agent使用文档.md §6): unchecking cancels the wait.
    page.get_by_label("等待收盘", exact=False).uncheck()
    page.wait_for_selector("[data-testid='wait-close-countdown']", state="detached", timeout=5_000)
    assert page.get_by_role("button", name="取消分析").count() == 0
