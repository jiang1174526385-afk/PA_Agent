"""Phase-5 "free chat + AI debug panel" browser e2e smoke suite.

Reuses the shared `live_server` fixture (real uvicorn + real
`AppContext.bootstrap()`, fake `TwoStageOrchestrator.submit` +
`FreeChatSession.send` -- see conftest.py's `_fake_submit`/`_fake_chat_send`).
"""

from __future__ import annotations

import pytest


def _submit_analysis(page, live_server) -> None:
    page.goto(live_server["base_url"])
    page.get_by_label("数据源").select_option("okx")
    page.wait_for_function("document.querySelector('[aria-label=\"品种\"]').options.length > 1")
    page.get_by_label("品种").select_option("BTC-USDT-SWAP")
    page.get_by_label("周期").select_option("15m")
    page.get_by_role("button", name="获取数据").click()
    page.wait_for_selector("[data-testid='chart-view'] canvas", timeout=15_000)
    page.wait_for_selector("button:has-text('提交分析'):not([disabled])", timeout=15_000)
    page.get_by_role("button", name="提交分析").click()


@pytest.mark.e2e
def test_chat_send_and_receive_reply(live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _submit_analysis(page, live_server)
    page.wait_for_selector("[data-testid='chat-panel']", timeout=15_000)

    chat_input = page.locator("[data-testid='chat-input']")
    page.wait_for_function(
        "() => !document.querySelector('[data-testid=\"chat-input\"]').disabled",
        timeout=15_000,
    )
    chat_input.fill("止损应该设多少？")
    page.get_by_role("button", name="发送").click()

    # The timeline shows both the user turn and the completed AI reply.
    page.wait_for_selector("text=用户: 止损应该设多少？", timeout=10_000)
    page.wait_for_selector("li.chat-timeline-item:has-text('✓')", timeout=10_000)

    # Switch to the raw-stream view: same underlying stream, e2e fake reply text.
    page.get_by_role("button", name="原始流").click()
    page.wait_for_selector("text=维持当前止损位不变", timeout=5_000)

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_debug_panel_shows_turns_with_masked_api_key(live_server, page):
    _submit_analysis(page, live_server)
    page.wait_for_selector("[data-testid='debug-panel']", timeout=15_000)

    debug_panel = page.locator("[data-testid='debug-panel']")
    debug_panel.wait_for()
    page.wait_for_selector(".debug-turn-item:has-text('Stage1 诊断')", timeout=10_000)
    page.wait_for_selector(".debug-turn-item:has-text('Stage2 决策')", timeout=10_000)

    # No plaintext API key anywhere on the page (settings.json in the e2e tmp
    # dir has an empty api_key, so this also guards against accidentally
    # rendering the literal empty-string sentinel as a real-looking secret).
    body_text = page.locator("body").inner_text()
    assert "sk-" not in body_text


@pytest.mark.e2e
def test_prompt_files_panel_lists_injected_files(live_server, page):
    _submit_analysis(page, live_server)
    page.wait_for_selector("[data-testid='prompt-files-panel']", timeout=15_000)

    # conftest's _fake_submit calls on_stage2_files(["e2e_strategy.txt"]) and
    # _build_record sets strategy_files_used=["e2e_strategy.txt"].
    page.wait_for_selector("text=e2e_strategy.txt", timeout=10_000)
