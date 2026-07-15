# PA Agent Web UI Development Reference

> Audience: a Claude picking up `pa_agent/webui/` dev/bug fixes in a brand-new conversation (zero prior context).
> Purpose: know which file a feature lives in, which files to also check when changing it, and what historical pitfalls/design decisions exist — without re-reading all seven `docs/webui_migration/phase-*-completion-report.md` files each time.
> Not a user manual — for button/interaction behavior see `PA_Agent使用文档.md` (that doc = "what happens when you click this"; this doc = "what code is behind it and what to watch for"). Different responsibilities — don't copy content between them. On inconsistency, actual code behavior wins; update the other doc.
> **This file is a router.** It holds the project overview, directory map, startup/build/test commands, and a task→sub-doc table. **Read only the specific sub-doc(s) the routing table below points to for your task — not everything.** Each sub-doc lists its own "also check" companions for tightly-coupled changes.
> **Read this file at the start of every new session that adds or modifies any Web UI (`pa_agent/webui/`) functionality**, per the user's standing instruction — before writing code, not after.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Document Map](#2-document-map)

---

## 1. Project Overview

### 1.1 Project Positioning

`pa_agent/webui/` (FastAPI + React/TypeScript) is the **primary, actively-developed interactive entry point** for PA Agent as of the `docs/webui_migration/` project's completion (7 phases, 2026-07-15/16). It has full functional parity with the legacy PyQt6 desktop GUI (`pa_agent/gui/`) — K-line chart, two-stage AI analysis, decision tree replay, animated decision-flow visualization, free chat + debug panel, demo replay, Feishu/PushPlus order-opportunity notifications — plus a trade-record analysis report page the desktop GUI never had. `pa_agent/gui/` remains supported and independently runnable but is legacy/reference-only: **new functionality is implemented in `pa_agent/webui/` only.**

Core business logic (`pa_agent/orchestrator/`, `pa_agent/data/`, `pa_agent/indicators/`, `pa_agent/config/`, `pa_agent/records/`, `pa_agent/notify/`, `pa_agent/util/`, `pa_agent/ai/`) is shared between the desktop GUI and the web layer — **the web layer calls these modules, it does not reimplement them.** When you need trading-domain math or trace formatting, check whether a pure function already exists in one of these packages before writing new TypeScript/Python logic. Two categories of desktop code exist relative to this rule:

- **Directly importable** (pure functions, no Qt/PyQt6 dependency): e.g. `pa_agent/ai/decision_tree.py::merge_traces`/`format_trace_answer`, `pa_agent/util/trade_metrics.py::compute_risk_reward`/`passes_trader_equation`, `pa_agent/data/bar_close_wait.py::seconds_until_bar_closes`. Import these directly from `pa_agent/webui/`.
- **Algorithm-only reusable** (the desktop class is a `QObject`/`QWidget` with Qt signals/timers, but its scheduling/layout *algorithm* is pure): e.g. `pa_agent/demo/replayer.py`'s step-building logic (ported into `pa_agent/webui/services/demo_runner.py::build_demo_steps()`), `pa_agent/gui/decision_flow_viz.py`'s node/edge layout math (re-expressed in `pa_agent/webui/frontend/src/decisionFlow/layout.ts`). You reimplement the *algorithm*, not the trading logic, and the docstring should say "mirrors `pa_agent/gui/X.py`'s Y" so the link isn't lost.

### 1.2 Two Visual Themes Coexist On Purpose

- **Dark theme** (`pa_agent/webui/frontend/src/styles/tokens.css`/`app.css`): the "live analysis workbench" — chart, decision panel, decision tree, decision flow, chat, debug, demo/notify. Mirrors `pa_agent/gui/theme/tokens.py`.
- **Light card-dashboard theme** (`pa_agent/webui/frontend/src/reportStyles/reportTokens.css`, prefix `--report-*`): the trade-record analysis report page only (`/reports`). Deliberately does **not** import `tokens.css` and has no desktop-GUI equivalent — it's a net-new feature designed from `qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg` (repo-root `qunyou/`, **not** under `pa_agent/`).

**Do not merge these themes or let one leak into the other.** If a change seems to require it, that's a decision for the user, not something to do "while you're in there."

### 1.3 Directory Structure

```
pa_agent/webui/
├── server.py                  # FastAPI app: mounts every router below + static SPA fallback (2 route trees: "/" dark workbench, "/reports" light dashboard, same bundle/index.html, client-side pathname routing in main.tsx)
├── deps.py                    # AppState (per-process singleton: orchestrator, data source registry, chat_session, chat_runner, demo_runner, etc.) + FastAPI dependency wiring
├── api/                       # Route layer — thin; business logic delegated to services/ or directly to pa_agent core packages
│   ├── kline.py                # REST: /api/data-sources, /api/symbols, /api/timeframes, /api/kline/snapshot; WS: /ws/kline — see 01_kline_and_chart.md
│   ├── analysis.py             # WS: /ws/analysis (submit/incremental/demo modes, cancel) — see 02_analysis_and_decision.md
│   ├── decision_tree.py        # REST: /api/decision-tree/static, /replay, /flow — see 03_decision_tree_and_flow.md
│   ├── chat.py                 # WS: /ws/chat; REST: /api/chat/debug-context — see 04_chat_and_debug.md
│   ├── demo.py                  # REST: /api/demo/records — see 05_demo_and_notify.md
│   ├── reports.py               # REST: /api/reports/* (trade-record dashboard) — see 06_reports_dashboard.md
│   ├── settings.py               # REST: /api/settings/{section} (provider/general/feishu/pushplus/okx) — see 07_settings_and_config.md
│   └── models.py                 # REST: /api/ai/models (hardcoded curated list, see 07_settings_and_config.md pitfalls)
├── schemas/                    # Pydantic response/request models, hand-kept mirror of frontend src/types/domain.ts (no codegen — see §1.5)
│   ├── kline.py / chat.py / decision_tree.py / demo.py / reports.py / settings.py
├── services/                    # asyncio equivalents of desktop QThread/QObject wrappers + pure view-model builders
│   ├── refresh_broadcaster.py    # RefreshBroadcaster: asyncio equivalent of pa_agent/data/refresh_loop.py::RefreshLoop — see 01_kline_and_chart.md
│   ├── analysis_runner.py         # AnalysisRunner: asyncio equivalent of pa_agent/gui/main_window.py::_AnalysisWorker — see 02_analysis_and_decision.md
│   ├── chat_runner.py              # ChatRunner/build_chat_session(): asyncio wrapper over pa_agent/orchestrator/free_chat.py::FreeChatSession — see 04_chat_and_debug.md
│   ├── demo_runner.py               # DemoRunner/build_demo_steps(): re-expresses pa_agent/demo/replayer.py's step algorithm as WS JSON messages — see 05_demo_and_notify.md
│   ├── order_alert.py                # maybe_alert_order_opportunity(): ports pa_agent/gui/order_opportunity.py's detect+broadcast half — see 05_demo_and_notify.md
│   ├── decision_shape.py              # decision_inner(): normalizes real-nested vs test-fixture-flat stage2_decision shape — see 02_analysis_and_decision.md §Gotcha
│   └── trade_metrics_view.py           # build_trade_metrics(): wraps pa_agent/util/trade_metrics.py's pure functions for the "record" WS message — see 02_analysis_and_decision.md
└── frontend/                    # Vite + React 19 + TypeScript, single bundle for both "/" and "/reports"
    └── src/
        ├── App.tsx                 # Orchestrates the dark workbench: submit/cancel, wait-for-close, chart freeze/resume, WS message routing — see 08_state_and_layout.md
        ├── main.tsx                 # Pathname-based routing ("/" vs "/reports"), no react-router
        ├── state/appStore.tsx        # Context+useReducer store for the dark workbench — see 08_state_and_layout.md
        ├── api/{client,paAgentApi,paAgentWs}.ts   # REST client + WS hooks (useKlineSocket/useAnalysisSocket/useChatSocket), epoch-based stale-frame filtering
        ├── types/domain.ts            # Hand-kept mirror of every schemas/*.py — see §1.5
        ├── toolbar/Toolbar.tsx         # Data source/symbol/timeframe, submit/incremental/cancel, wait-for-close checkbox+countdown, demo picker, resume-chart button
        ├── chart/                      # ChartView.tsx, useLightweightChart.ts, decisionOverlay.ts — see 01_kline_and_chart.md
        ├── decision/                   # DecisionPanel.tsx, FutureTrendPanel.tsx — see 02_analysis_and_decision.md
        ├── decisionTree/ decisionFlow/  # DecisionTreePanel.tsx; DecisionFlowPanel.tsx (react-flow) — see 03_decision_tree_and_flow.md
        ├── chat/ debug/                 # ChatPanel.tsx, useChatSession.ts; DebugPanel.tsx, ValidationDialog.tsx — see 04_chat_and_debug.md
        ├── demo/ notify/                 # demoFormat.ts; OrderOpportunityToast.tsx — see 05_demo_and_notify.md
        ├── reports/ reportStyles/          # Trade-record dashboard, light theme, separate from everything above — see 06_reports_dashboard.md
        ├── settings/                       # SettingsModal.tsx + 5 tabs (Provider/General/Feishu/PushPlus/OKX) — see 07_settings_and_config.md
        └── styles/                          # tokens.css/app.css (dark theme only; reportStyles/ is separate)
```

### 1.4 Boundaries With `pa_agent/gui/` (Legacy Desktop GUI)

- `pa_agent/gui/` is never modified for web-layer needs. If a bug or missing feature is found there, it's a separate, explicitly-scoped task — not something to fix "while touching the web layer."
- The desktop GUI's file-per-widget layout (`decision_panel.py`, `decision_tree_panel.py`, `decision_flow_viz.py`, `conversation_widget.py`, `ai_stream_window.py`, `debug_widget.py`, `prompt_files_panel.py`, `validation_debug_dialog.py`, `order_opportunity.py`, `future_trend_panel.py`) is the **behavioral reference** when porting a feature — read the relevant desktop file(s) fully before writing the web equivalent, per each sub-doc's "desktop reference" pointer.
- Full inventory and migration history: `docs/webui_migration/README.md` (master plan) and its 7 `phase-N-completion-report.md` files (design decisions, pitfalls hit, what was deferred). This dev-guide extracts the durable facts from those reports; the reports themselves are the historical record — consult them for "why was it built this way" that isn't repeated here.

### 1.5 Cross-Cutting Invariants (apply to every sub-doc)

- **WS message schemas are hand-kept, not code-generated.** `pa_agent/webui/schemas/*.py` (Pydantic) and `pa_agent/webui/frontend/src/types/domain.ts` (TypeScript) must be manually kept in sync. When adding a field: **only add, never delete/rename** an existing field on either side without checking every consumer (this project's whole migration history is full of "new field, zero existing fields touched" — that discipline is why 7 phases of e2e regressions never broke each other).
- **Secrets never round-trip in plaintext.** `config/settings.json`'s API keys/webhook secrets/tokens are masked in every API response (`xxx_set: bool` sibling field pattern); `PUT` accepts `None` = unchanged, `""` = clear. See `07_settings_and_config.md`.
- **`stage2_decision` has two real shapes**: production AI output is nested (`{"decision": {order_type, ...}, "decision_trace": [...]}`), but this project's test fixtures (going back to phase 1) are flat (fields directly at the top level). Both frontend (`DecisionPanel.tsx`/`FutureTrendPanel.tsx`) and backend (`decision_shape.py::decision_inner()`) normalize this — **this is a permanent dual-shape reality, not a temporary hack to eventually delete.** See `02_analysis_and_decision.md`.
- **`.app-shell`'s vertical layout budget is tight.** It's `min-height: 100vh` (not fixed `100vh`, changed in phase 5 to allow scrolling), and by phase 6 already holds: toolbar, chart+side-pane (`main-layout`), `.flow-row` (480px), `.chat-debug-row` (~420px). **Before adding another stacked block to the dark workbench, run the *entire* Playwright e2e suite (not just your new scenario) — a phase-5 regression (existing phase-3 test broke from a phase-5 CSS change) was only caught this way.** See `08_state_and_layout.md`.
- **Shared test fixtures (`tests/webui/conftest.py`, `tests/webui/e2e/conftest.py`) are used by every phase's tests.** Adding a field to `_build_record`/`FakeDataSource` is safe (additive); before changing shared fixture *behavior* (e.g. a monkeypatch), run both "new test alone" and "new test alongside its sibling test file" — a phase-6 bug (module-level import caching of `RECORDS_PENDING_DIR` in `pa_agent/demo/record_loader.py`) only reproduced when tests ran together. See `09_testing_and_pitfalls.md`.

### 1.6 Startup and Build

```bash
# Backend + already-built frontend, http://127.0.0.1:8765
python start_webui.py
python start_webui.py --reload      # backend hot-reload; frontend still needs a manual rebuild

# Or via Makefile:
make run-webui                       # same as start_webui.py
make dev-webui-frontend               # Vite dev server, proxies /api and /ws to 127.0.0.1:8765 (run make run-webui in another terminal first)
make build-webui-frontend              # builds to pa_agent/webui/static/pa_agent_app/

cd pa_agent/webui/frontend
npm install
npm run dev                          # standalone frontend dev server
npm run build                        # output -> ../static/pa_agent_app/
```

**After changing any file under `pa_agent/webui/frontend/src`, run `npm run build`** if you need the served app (`/`, `/reports`) to reflect it — `pa_agent/webui/static/pa_agent_app/` is a static build artifact.

**`npm run build` will delete-then-recreate `pa_agent/webui/static/pa_agent_app/`, which clobbers the Git-tracked `.gitkeep` placeholder in that directory** (`.gitignore` ignores everything else there). After building, check `git status` and `git checkout -- pa_agent/webui/static/pa_agent_app/.gitkeep` if it shows as deleted — every phase from 5 onward has hit this.

### 1.7 The Four Verification Commands

```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # type checking
npx vitest run           # unit tests (49 tests / 9 files as of phase 7)
npm run build             # build (also clobbers .gitkeep, see §1.6)

cd /home/jack/quant_trading_system_v2/PA_Agent
./.venv/bin/pytest tests/webui/ -q --ignore=tests/webui/e2e     # backend, 64 passed as of phase 7
./.venv/bin/pytest tests/webui/e2e/ --browser chromium          # Playwright e2e, real Chromium, 23 scenarios as of phase 7
```

The e2e suite runs against a **real uvicorn instance with a real `AppContext.bootstrap()`** — OKX/TradingView data sources hit the real network (no auth needed for public market data), only `TwoStageOrchestrator.submit`/`FreeChatSession.send` are monkeypatched to fast deterministic fakes (no paid API key needed). Settings/records paths are redirected to a tmp dir via the shared `live_server` fixture. See `09_testing_and_pitfalls.md` for fixture details and known flakiness sources.

**No CI in this repo** — these four commands are the acceptance gate; run them yourself before considering a change done. This mirrors `docs/webui_migration/README.md` §3.3's "session-end gate" that governed the whole migration (all four verification types must have *actually run*, not be assumed).

### 1.8 Division of Responsibility Among Existing Documents

| Document | Responsibility | Audience |
| --- | --- | --- |
| Root `README.md` | Top-level entry-point description (Web UI is now the primary one; desktop GUI is legacy) | Humans, first time learning about the project |
| `PA_Agent使用文档.md` | **User-facing** description of button/interaction behavior (written desktop-first, functionally at parity with the web UI) | Human users; usable by Claude as a reference for "what this feature means to the user" — but code wins on conflict |
| **This document**, `docs/dev_guide/webui.md` | **Routing entry point** — project overview, directory map, commands, task→sub-doc table | Claude (first-hand reference for a brand-new conversation with zero context) — **read at the start of every session touching `pa_agent/webui/`** |
| `docs/dev_guide/*.md` | Code-facing architecture, invariants, cross-module dependencies, and historical pitfalls, split by topic | Claude — read only the sub-doc(s) relevant to the current task |
| `docs/webui_migration/README.md` + `phase-*-completion-report.md` | **Historical record** of the 7-phase migration project (now complete) — design decisions, what was deferred, why, exact verification commands/results per phase | Consult for "why was it built this way" that isn't repeated in the dev-guide sub-docs; do not treat as a live architecture reference (code may have moved on since) |
| `docs/图表K线与分析快照说明.md`, `docs/获取数据功能说明.md` | Standalone explainers for specific desktop-GUI behaviors (chart freeze-on-analysis semantics, data-fetch mechanics) that predate the web migration | Background reading when a chart/data-source question needs the original rationale |

**Rule: don't restate `PA_Agent使用文档.md`'s behavior descriptions here or in the sub-docs — only what's unique to this reference (code location, dependencies, pitfalls).** New dev-reference content belongs in the relevant `docs/dev_guide/*.md` sub-doc, not appended back into this file.

---

## 2. Document Map

Route by task/keyword. Read only the sub-doc(s) your task's row points to, then that sub-doc's own "also check" note for anything tightly coupled.

| Sub-doc | Covers | Task/keyword | Common companion files |
| --- | --- | --- | --- |
| `docs/dev_guide/01_kline_and_chart.md` | `RefreshBroadcaster`/`/ws/kline`, `ChartView.tsx`/`useLightweightChart.ts`, decision price-line overlay, chart freeze-on-submit + manual resume (phase 7), wait-for-bar-close checkbox + countdown (phase 7, `bar_close_wait.py`) | Data-source/symbol/timeframe switching, K-line streaming, chart flicker/NaN, entry/SL/TP price lines on the chart, "等待收盘", "图表实时更新" resume button, `is_forming`/`seconds_until_close` | `02_analysis_and_decision.md` (submit gating on `hasFrame`), `08_state_and_layout.md` (App.tsx orchestration of freeze/wait state), `07_settings_and_config.md` (refresh interval) |
| `docs/dev_guide/02_analysis_and_decision.md` | `AnalysisRunner`/`/ws/analysis` (full/incremental/demo modes, cancel, single-flight), `DecisionPanel.tsx`/`FutureTrendPanel.tsx`, the nested-vs-flat `stage2_decision` shape gotcha + its fix, trader-equation/win-rate/risk-reward display (`trade_metrics_view.py`, phase 7) | Submit/incremental analysis, cancel mid-analysis, decision panel fields, "决策"标签, 交易者方程/预估胜率/风险回报比, `decision.decision` unwrap bug | `01_kline_and_chart.md` (submit gating, chart freeze), `03_decision_tree_and_flow.md` (same record's trace data), `04_chat_and_debug.md` (chat session rebuilt on each new record) |
| `docs/dev_guide/03_decision_tree_and_flow.md` | `/api/decision-tree/{static,replay,flow}`, `DecisionTreePanel.tsx` (text replay), `DecisionFlowPanel.tsx` (react-flow animated diagram), `layout.ts` geometry, `decision_flow_auto_play`/`decision_flow_play_seconds` settings | 决策树/决策树可视化 tabs, gate/decision trace rendering, flow-diagram nodes/edges/animation, autoplay/fullscreen, `merge_traces`/`format_trace_answer` reuse | `02_analysis_and_decision.md` (source record), `07_settings_and_config.md` (autoplay settings), `08_state_and_layout.md` (`.flow-row` layout budget) |
| `docs/dev_guide/04_chat_and_debug.md` | `ChatRunner`/`build_chat_session()`/`/ws/chat`, `ChatPanel.tsx` (timeline + raw-stream toggle), `DebugPanel.tsx` (merged debug + prompt-files panel), `ValidationDialog.tsx`, `/api/chat/debug-context`, secret masking | Free-chat follow-up, "实时"/"原始"/"调试" tabs, JSON-validation-failure dialog, prompt files list, token usage | `02_analysis_and_decision.md` (chat session rebuilt when a new record arrives), `08_state_and_layout.md` (`.chat-debug-row` layout budget) |
| `docs/dev_guide/05_demo_and_notify.md` | `DemoRunner`/`build_demo_steps()`, `/api/demo/records`, demo mode inside `/ws/analysis` (`mode: "demo"`), `order_alert.py::maybe_alert_order_opportunity`, `OrderOpportunityToast.tsx`, Feishu/PushPlus trigger wiring | 演示模式/demo replay, 下单机会通知/order-opportunity toast, `notify_on_order_only` (known no-op field, don't wire it without asking), `save_trade_record()` (known NOT wired to the web layer — confirm with user before changing) | `02_analysis_and_decision.md` (`/ws/analysis` shares this WS with demo mode), `09_testing_and_pitfalls.md` (`RECORDS_PENDING_DIR` module-cache pitfall) |
| `docs/dev_guide/06_reports_dashboard.md` | `/api/reports/*`, `pa_agent/records/report_metrics.py`/`trade_fill_backfill.py`, light-theme `src/reports/`+`src/reportStyles/`, KPI cards, 9 chart components (recharts), order table | Trade-record analysis report page (`/reports`), KPI/metric formulas, CSV backfill from MT5/OKX, 净值曲线/月度收益/盈亏日历/etc. charts, light theme | None — this page is intentionally isolated from everything else (own theme, own data source, own route); only `07_settings_and_config.md` (OKX credentials tab) is a real dependency |
| `docs/dev_guide/07_settings_and_config.md` | `/api/settings/{provider,general,feishu,pushplus,okx}`, `SettingsModal.tsx` + 5 tabs, secret masking pattern, `decision_flow_play_seconds` (exists, don't reintroduce as a "gap"), `GET /api/ai/models` (hardcoded list, known limitation) | Settings dialog, adding a new config field/section, API key handling, provider/model selection, decision-flow autoplay/zoom/duration settings, OKX credentials for the reports backfill | `06_reports_dashboard.md` (OKX tab), `03_decision_tree_and_flow.md` (autoplay settings consumed there) |
| `docs/dev_guide/08_state_and_layout.md` | `App.tsx` (orchestrates submit/cancel/wait-for-close/chart-freeze/demo/WS routing), `appStore.tsx` (Context+useReducer), `Toolbar.tsx`, `.app-shell` layout-budget history (100vh → min-height, phase 5 regression story) | Adding new App.tsx state/wiring, toolbar controls, cross-panel state, "why did adding a new block break an unrelated e2e test" | `01_kline_and_chart.md`, `02_analysis_and_decision.md`, `03_decision_tree_and_flow.md`, `04_chat_and_debug.md` (each panel this file mounts) |
| `docs/dev_guide/09_testing_and_pitfalls.md` | Test commands (see §1.7), `tests/webui/conftest.py`/`e2e/conftest.py` fixture patterns (`FakeDataSource`, `live_server`, `_build_record`), module-level-import-caching pitfall, `.gitkeep` build clobber, misc cross-phase pitfalls not owned by a more specific sub-doc | Writing new tests, "why did my test pass alone but fail in the full suite", shared fixture changes, e2e flakiness | Points back to the sub-doc that owns the feature the failing test covers |

**When in doubt**: match the file/feature you're touching to §1.3's directory map, then to a row above; if a task spans multiple rows (e.g. "add a new WS message field consumed by both the decision panel and the debug panel"), read all the rows it touches — each sub-doc's own "also check" line will confirm you found the complete set.
