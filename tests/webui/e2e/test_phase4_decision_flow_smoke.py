"""Phase-4 "DecisionFlowViz" (animated branched flowchart) browser e2e smoke
suite.

Reuses the phase-1 `live_server` fixture (real uvicorn + real
`AppContext.bootstrap()`, fake `TwoStageOrchestrator.submit` -- see
conftest.py's `_build_record`, which supplies gate_trace + decision_trace +
terminal so this panel has something to render).
"""

from __future__ import annotations

import json
import time
import urllib.request

import pytest


def _configure_fast_autoplay(live_server, *, seconds: int) -> None:
    """`decision_flow_auto_play` defaults to True (see
    pa_agent/config/settings.py); shrink `decision_flow_play_seconds` before
    the page loads so the e2e suite doesn't sit through a real 50s camera
    flight (mirrors desktop's `_play_duration_seconds`)."""
    req = urllib.request.Request(
        f"{live_server['base_url']}/api/settings/general",
        data=json.dumps({"decision_flow_play_seconds": seconds}).encode(),
        headers={"Content-Type": "application/json"},
        method="PUT",
    )
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200


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
def test_decision_flow_panel_renders_nodes_and_terminal(live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _configure_fast_autoplay(live_server, seconds=2)
    _submit_analysis(page, live_server)

    page.wait_for_selector("[data-testid='decision-flow-panel']", timeout=15_000)
    page.wait_for_selector("[data-testid='flow-terminal-node']", timeout=15_000)

    # conftest's fake record has gate_trace=[1.1] + decision_trace=[9.0, 10.3].
    flow_panel = page.locator("[data-testid='decision-flow-panel']")
    decision_nodes = flow_panel.locator("[data-testid='flow-decision-node']")
    assert decision_nodes.count() == 3
    assert flow_panel.locator("[data-node-id='10.3']").count() == 1

    terminal = page.locator("[data-testid='flow-terminal-node']")
    assert "TRADE" in terminal.inner_text().upper() or "交易" in terminal.inner_text()

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_decision_flow_autoplay_runs_and_finishes_without_errors(live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    _configure_fast_autoplay(live_server, seconds=2)
    _submit_analysis(page, live_server)

    page.wait_for_selector("[data-testid='decision-flow-panel']", timeout=15_000)
    page.wait_for_selector("[data-testid='flow-terminal-node']", timeout=15_000)

    # decision_flow_auto_play defaults to True -- playback should start on its
    # own shortly after the flow loads (mirrors desktop
    # `should_auto_play_after_load()` / `play_path()`).
    page.wait_for_selector("text=路径播放中", timeout=5_000)

    # Clicking the canvas mid-playback stops it (mirrors desktop's
    # eventFilter-based click-to-cancel) -- exercise it, then wait for either
    # outcome (cancelled or naturally finished) so the suite stays fast.
    time.sleep(0.3)
    page.locator(".decision-flow-canvas").click(position={"x": 5, "y": 5})

    # Playback status must clear (stopped or finished) within a bounded wait.
    page.wait_for_function(
        "() => !document.body.innerText.includes('路径播放中')",
        timeout=6_000,
    )

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_decision_flow_fullscreen_toggle(live_server, page):
    _configure_fast_autoplay(live_server, seconds=2)
    _submit_analysis(page, live_server)

    page.wait_for_selector("[data-testid='decision-flow-panel']", timeout=15_000)
    page.wait_for_selector("[data-testid='flow-terminal-node']", timeout=15_000)

    page.get_by_role("button", name="全屏推演").click()
    assert "fullscreen" in (page.locator("[data-testid='decision-flow-panel']").get_attribute("class") or "")

    page.get_by_role("button", name="退出全屏").click()
    assert "fullscreen" not in (page.locator("[data-testid='decision-flow-panel']").get_attribute("class") or "")
