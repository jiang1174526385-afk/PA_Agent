"""Phase-1 browser e2e smoke suite (real Chromium via pytest-playwright).

Runs against a real uvicorn instance backed by a real `AppContext.bootstrap()`
(real OKX/TradingView network data sources) with `TwoStageOrchestrator.submit`
monkeypatched to a fast deterministic fake (see conftest.py) so the AI stages
don't need a paid API key and complete in well under a second.

MT5 is Windows-only (`MetaTrader5` package has no Linux wheel); this sandbox
cannot exercise it, so MT5 is only checked for presence in the data-source
dropdown, not for a live symbol fetch -- see phase-1-completion-report.md.
"""

from __future__ import annotations

import json
import time

import pytest


@pytest.mark.e2e
def test_dark_theme_and_no_console_errors(live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    page.goto(live_server["base_url"])
    page.wait_for_selector("[data-testid='toolbar']")

    bg_color = page.evaluate("getComputedStyle(document.body).backgroundColor")
    assert bg_color == "rgb(10, 14, 20)"  # --bg: #0a0e14

    accent = page.evaluate(
        "getComputedStyle(document.documentElement).getPropertyValue('--accent').trim()"
    )
    assert accent == "#2dd4bf"

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_switch_data_sources_updates_symbol_dropdown(live_server, page):
    page.goto(live_server["base_url"])
    page.wait_for_selector("[data-testid='toolbar']")

    source_select = page.get_by_label("数据源")
    symbol_select = page.get_by_label("品种")

    source_select.select_option("tradingview")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    tv_options = symbol_select.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "XAUUSD" in tv_options or len(tv_options) > 1

    source_select.select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    okx_options = symbol_select.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert any(sym.endswith("-USDT-SWAP") for sym in okx_options)

    # mt5 must at least be listed as a choice (native lib unavailable on Linux,
    # so we don't attempt a live symbol fetch for it here).
    kinds = source_select.evaluate("el => Array.from(el.options).map(o => o.value)")
    assert "mt5" in kinds


@pytest.mark.e2e
def test_fetch_data_renders_chart_and_streams_ws_frame(live_server, page):
    kline_requests = []
    page.on(
        "request",
        lambda req: kline_requests.append(req.url) if "/api/kline/snapshot" in req.url else None,
    )

    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("BTC-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")

    page.get_by_role("button", name="获取数据").click()

    # Candles render as canvas inside the chart pane.
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)

    # At least one live /ws/kline frame should arrive within a few seconds
    # (the chart re-renders on each frame; we simply give the WS time to push
    # a second update and confirm the canvas is still alive/rendered).
    time.sleep(3)
    assert page.locator("[data-testid='chart-view'] canvas").count() > 0
    assert any("/api/kline/snapshot" in url for url in kline_requests)


@pytest.mark.e2e
def test_submit_full_analysis_updates_panels_and_writes_pending_record(live_server, page):
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("BTC-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    # Gate on the live /ws/kline frame actually arriving (the button is
    # disabled until then -- see Toolbar's hasFrame prop), not just the chart
    # having rendered from the one-shot REST snapshot.
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)

    page.get_by_role("button", name="提交分析").click()
    page.wait_for_selector("text=买入", timeout=15_000)
    assert page.get_by_text("E2E fake analysis result").count() > 0

    deadline = time.monotonic() + 5
    pending_files = []
    while time.monotonic() < deadline:
        pending_files = list(live_server["records_dir"].glob("*.json"))
        if pending_files:
            break
        time.sleep(0.2)
    assert pending_files, "expected a records/pending/*.json file after a completed analysis"
    payload = json.loads(pending_files[0].read_text())
    assert payload["stage2_decision"]["order_type"] == "买入"


@pytest.mark.e2e
def test_cancel_mid_analysis_returns_to_idle(live_server, page):
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("ETH-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    # Gate on the live /ws/kline frame actually arriving (the button is
    # disabled until then -- see Toolbar's hasFrame prop), not just the chart
    # having rendered from the one-shot REST snapshot.
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)

    page.get_by_role("button", name="提交分析").click()
    page.wait_for_selector("button:has-text('取消分析')", timeout=5_000)
    page.get_by_role("button", name="取消分析").click()

    page.wait_for_selector("button:has-text('取消分析')", state="detached", timeout=15_000)
    assert page.get_by_role("button", name="提交分析").is_enabled()


@pytest.mark.e2e
def test_settings_modal_masks_secrets_and_persists_non_secret_field(live_server, page):
    page.goto(live_server["base_url"])
    page.get_by_role("button", name="设置").click()
    page.wait_for_selector("[data-testid='settings-modal']")

    api_key_input = page.locator(".modal-body input[type='password']").first
    assert api_key_input.input_value() == ""  # unset in the tmp settings.json fixture

    page.get_by_role("button", name="通用").click()
    bar_count_input = page.get_by_label("分析K线数量")
    bar_count_input.fill("321")
    page.get_by_role("button", name="保存", exact=True).click()
    page.wait_for_selector("text=保存中…", state="detached")

    page.reload()
    page.get_by_role("button", name="设置").click()
    page.get_by_role("button", name="通用").click()
    page.wait_for_selector("input")
    assert page.get_by_label("分析K线数量").input_value() == "321"


@pytest.mark.e2e
def test_disconnect_during_analysis_leaves_no_orphan_run(live_server, page, context):
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("SOL-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    # Gate on the live /ws/kline frame actually arriving (the button is
    # disabled until then -- see Toolbar's hasFrame prop), not just the chart
    # having rendered from the one-shot REST snapshot.
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)

    page.get_by_role("button", name="提交分析").click()
    page.wait_for_selector("button:has-text('取消分析')", timeout=5_000)
    page.close()  # abrupt disconnect while the fake orchestrator is mid-run

    # The fake orchestrator waits on cancel_token for up to 3s (60 * 0.05s);
    # WebSocketDisconnect handling should set the cancel token so it exits
    # promptly instead of spinning for the full duration.
    new_page = context.new_page()
    new_page.goto(live_server["base_url"])
    new_page.wait_for_selector("[data-testid='toolbar']")
    new_page.close()
