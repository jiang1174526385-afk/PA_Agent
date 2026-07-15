"""Phase-3 "decision tree replay panel" browser e2e smoke suite.

Reuses the phase-1 `live_server` fixture (real uvicorn + real
`AppContext.bootstrap()`, fake `TwoStageOrchestrator.submit` -- see
conftest.py's `_build_record`, which now includes a small gate_trace/
decision_trace/terminal so this panel has something to render).
"""

from __future__ import annotations

import time

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
def test_decision_tree_panel_renders_terminal_and_path_rows(live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _submit_analysis(page, live_server)

    page.wait_for_selector("[data-testid='decision-tree-panel']", timeout=15_000)
    # Terminal banner shows the e2e-fake terminal outcome (trade -> §10.3).
    page.wait_for_selector("text=§10.3", timeout=15_000)
    assert page.get_by_text("满足下单条件").count() > 0

    # Path replay table has one row per gate_trace + decision_trace item (1 + 2 = 3).
    rows = page.locator(".decision-tree-path-table tbody tr")
    assert rows.count() == 3
    assert page.get_by_text("闸门").count() > 0
    assert page.get_by_text("策略").count() > 0

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_decision_tree_path_row_click_highlights_full_tree_node(live_server, page):
    _submit_analysis(page, live_server)
    page.wait_for_selector("[data-testid='decision-tree-panel']", timeout=15_000)
    page.wait_for_selector("text=§10.3", timeout=15_000)

    # Full tree section §10 must auto-expand because node 10.3 was visited.
    tree_section = page.locator("[data-section-id='10']")
    assert tree_section.get_attribute("open") is not None

    # Click the path-table row for node 10.3 and confirm the matching full-tree
    # row is scrolled into view / selected (mirrors desktop _scroll_tree_to_node).
    page.locator(".decision-tree-path-table [data-node-id='10.3']").click()
    time.sleep(0.3)  # smooth-scroll settle
    selected_tree_row = page.locator(".decision-tree-node-table tr.selected")
    assert selected_tree_row.count() == 1
    assert selected_tree_row.get_attribute("data-node-id") == "10.3"
