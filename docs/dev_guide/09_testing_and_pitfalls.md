# 09 — Testing Commands, Fixture Patterns, and Misc Pitfalls

> Router: `docs/dev_guide/webui.md`. Read this doc before writing new tests, when a test passes alone but fails in the full suite, or when a pitfall doesn't fit a more specific sub-doc above.

## 1. The Four Verification Commands (see `webui.md` §1.7 for the canonical copy)

```bash
cd pa_agent/webui/frontend
npx tsc --noEmit
npx vitest run
npm run build            # clobbers static/pa_agent_app/.gitkeep — see webui.md §1.6

cd /home/jack/quant_trading_system_v2/PA_Agent
./.venv/bin/pytest tests/webui/ -q --ignore=tests/webui/e2e
./.venv/bin/pytest tests/webui/e2e/ --browser chromium
```

**No CI exists in this repo — run all four yourself, every time, before calling a change done.** This mirrors `docs/webui_migration/README.md` §3.3's session-end gate that governed the entire 7-phase migration: a phase could not be marked complete without every verification type having *actually been run and its output actually read* — not assumed passing because "the change looks small."

## 2. e2e Fixture Architecture

- **`tests/webui/e2e/conftest.py::live_server`** — spins up a **real uvicorn instance** with a **real `AppContext.bootstrap()`** (so OKX/TradingView data sources hit the real network — no auth needed for public market data), with `TwoStageOrchestrator.submit` and `FreeChatSession.send` monkeypatched to fast, deterministic fakes (`_fake_submit`, `_fake_chat_send`) so tests don't need a paid AI API key and complete in well under a second. Settings/records paths are redirected to a tmp dir so the suite never touches the real `config/settings.json` or `records/pending/`.
- **`tests/webui/e2e/conftest.py::_build_record`** — the shared fake-`AnalysisRecord` builder used across phase 1–7 e2e suites, using the **flat** `stage2_decision` shape (see `02_analysis_and_decision.md`'s nested-vs-flat note — this is a deliberate, permanent test convention, not something to "fix" to match production nesting). Adding a new field to it is always safe (additive); before deleting/renaming a field, grep every test file that references it first — it's shared by every phase's e2e suite.
- **`tests/webui/conftest.py::FakeDataSource`** — the backend-pytest-level fake `DataSource`, used by `test_kline_api.py` and others for constructing forming/closed-bar test frames without a real MT5/OKX connection.
- MT5 is Windows-only (`MetaTrader5` has no Linux wheel) — e2e tests only check it's present in the data-source dropdown, never do a live MT5 symbol fetch. This is an accepted, permanent sandbox limitation, not a gap to close.

## 3. The Module-Level-Import-Caching Pitfall (hit once, worth knowing about)

`pa_agent.demo.record_loader` does `from pa_agent.config.paths import RECORDS_PENDING_DIR` **at module-import time**, copying the path *value* into its own module's namespace. `live_server`'s original fixture only did `monkeypatch.setattr("pa_agent.config.paths.RECORDS_PENDING_DIR", records_dir)` — patching the attribute on `paths`, not the copy already sitting in `record_loader`'s namespace. Because Python only imports a module once per process, whichever test ran first got its tmp dir permanently baked into `record_loader`'s copy, and every subsequent test in the same process saw that first test's leftover demo-record files on disk — a bug that **only reproduces when two tests using this module run together**, never when either runs alone.

**The generalizable lesson**: before changing a shared test fixture's *behavior* (not just adding a field), run the affected test file both **alone** and **alongside its sibling test files in the same run** — a single passing run in isolation proves nothing about cross-test contamination. This exact two-mode check is now explicit project convention (`webui.md` §1.5) after being learned the hard way in phase 6.

## 4. Other Cross-Cutting Pitfalls

- **`npm run build` deletes and recreates `pa_agent/webui/static/pa_agent_app/`, clobbering the Git-tracked `.gitkeep`** placeholder (`.gitignore` ignores everything else in that directory). Check `git status` after every local build and `git checkout -- pa_agent/webui/static/pa_agent_app/.gitkeep` if needed — every phase from 5 onward has hit this and had to remember to restore it before committing.
- **`decision_flow_auto_play` defaults to `True` with a 50-second `decision_flow_play_seconds` default** — an e2e test that doesn't account for this will either wait 50 real seconds or race the animation. Pattern used since phase 4: `PUT /api/settings/general` directly (bypassing the settings-modal UI) to shrink `decision_flow_play_seconds` to something like 2 seconds, **before** `page.goto()` — because (see `08_state_and_layout.md` §3) there's no live settings-invalidation mechanism, so changing it after the page has already loaded and mounted `DecisionFlowPanel` won't take effect for that page instance.
- **Frontend test-only labels (`data-testid`) exist for exactly the elements Playwright needs to target reliably** — `chart-view`, `toolbar`, `demo-record-select`, `demo-play-button`, `demo-random-button`, `order-opportunity-toast`, `wait-close-countdown`, `resume-chart-button`, `debug-panel`, `prompt-files-panel`, `settings-modal`. If you add a new interactive element that an e2e test needs to find deterministically (not via visible text, which can be ambiguous or i18n-fragile), add a `data-testid`, following this existing naming style (kebab-case, feature-prefixed).
- **`<label>`/`<input>` must use `htmlFor`/`id` pairing (or nest the input inside the label), not sibling divs** — Playwright's `get_by_label` (and screen readers) can't otherwise associate them. All settings-tab forms follow this since a phase-1 fix; keep following it for new form fields.
