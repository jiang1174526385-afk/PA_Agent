"""Phase-2 "trade record analysis report" browser e2e smoke suite.

Reuses the phase-1 `live_server` fixture (real uvicorn + real
`AppContext.bootstrap()`, fake `TwoStageOrchestrator.submit`) and additionally
chdirs into a tmp directory with a pre-seeded `trade_records/<key>.csv` so
`/reports` has something to render, without touching the real repo's
`trade_records/` directory.
"""
from __future__ import annotations

import csv
from pathlib import Path

import pytest

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
def reports_seed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_csv(
        tmp_path / "trade_records" / "XAUUSDm_15m.csv",
        [
            {"record_time": "2026-01-01 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
             "decision_stance": "balanced", "order_direction": "做多", "entry_price": "2000.0"},
            {"record_time": "2026-01-02 00:00:00", "symbol": "XAUUSDm", "timeframe": "15m",
             "decision_stance": "balanced", "order_direction": "做空", "entry_price": "2010.0"},
        ],
    )
    return tmp_path


@pytest.mark.e2e
def test_reports_page_light_theme_and_kpis_render(reports_seed, live_server, page):
    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda exc: console_errors.append(str(exc)))

    page.goto(f"{live_server['base_url']}/reports")
    page.wait_for_selector("[data-testid='reports-sidenav']")

    # Light theme, independent from phase-1 dark workbench (§2.1) --
    # phase-1's body background is rgb(10, 14, 20); this page's shell must differ.
    shell_bg = page.evaluate(
        "getComputedStyle(document.querySelector('.reports-shell')).backgroundColor"
    )
    assert shell_bg != "rgb(10, 14, 20)"
    assert "rgb(24" in shell_bg or "rgb(244" in shell_bg  # #f4f6fb ~ rgb(244, 246, 251)

    page.wait_for_selector("text=总收益", timeout=10_000)
    assert page.get_by_text("最大回撤").count() > 0
    assert page.get_by_text("盈利因子").count() > 0
    assert page.get_by_text("胜率").count() > 0

    assert console_errors == [], f"unexpected console errors: {console_errors}"


@pytest.mark.e2e
def test_reports_placeholder_routes_show_under_construction(reports_seed, live_server, page):
    page.goto(f"{live_server['base_url']}/reports")
    page.wait_for_selector("[data-testid='reports-sidenav']")

    page.get_by_text("报告对比").click()
    page.wait_for_selector("[data-testid='reports-placeholder']")
    assert page.get_by_text("开发中").count() > 0


@pytest.mark.e2e
def test_backfill_button_and_order_table_render(reports_seed, live_server, page):
    page.goto(f"{live_server['base_url']}/reports")
    page.wait_for_selector("[data-testid='order-table']")

    # MT5 backfill against a real (unavailable in this sandbox) terminal is
    # expected to fail cleanly rather than hang -- we only assert the button
    # is wired and a response (success or failure message) appears.
    page.get_by_role("button", name="回填真实成交").click()
    page.wait_for_function(
        "document.querySelector('.reports-kpi-sub')?.textContent?.length > 0", timeout=10_000
    )

    page.wait_for_selector("table.reports-order-table")
    assert page.locator("table.reports-order-table tbody tr").count() >= 1
