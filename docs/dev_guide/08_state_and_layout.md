# 08 — Global State, App.tsx Orchestration, and the Layout Budget

> Router: `docs/dev_guide/webui.md`. Read this doc before adding new `App.tsx` state, a new stacked block to the dark workbench, or a new toolbar control.

## 1. Architecture

- **`src/state/appStore.tsx`** — Context + `useReducer` store, holding the "core" dark-workbench state: `source`/`symbol`/`timeframe`/`nBars`, `analysisInProgress`, `statusMessage`/`errorMessage`, `record` (the current `AnalysisRecord`), `streamBuffers` (stage1/stage2 reasoning+content accumulators).
- **`App.tsx`** is the orchestrator — it does *not* delegate all state to `appStore`; several feature-specific pieces of state deliberately live as local `useState` in `App.tsx` instead (demo records/id/running, order-alert message, trade metrics, wait-for-close, chart-freeze). The project's convention (established phase 6, continued phase 7): **route genuinely new, mostly-independent UI concerns through local `App.tsx` state rather than growing the shared reducer for every feature** — only put something in `appStore`'s reducer if multiple components need it *and* it participates in the reducer's existing action vocabulary (submit/record/stream chunk lifecycle). When in doubt, look at how phase 6 (`demoRecords`/`demoRecordId`/`demoRunning`/`orderAlert`) and phase 7 (`tradeMetrics`/`waitForClose`/`pendingSubmitMode`/`chartFrozen`/`frozenFrame`) both added local state rather than reducer actions, and follow that precedent.
- **`Toolbar.tsx`** is a pure presentational component — all its props are passed down from `App.tsx`, it owns no state of its own. When adding a toolbar control, add the state/handler to `App.tsx`, pass down as props, same pattern as every existing control.
- **WS message routing**: `App.tsx`'s `useAnalysisSocket(callback)` has one big `switch (msg.type)` handling every `/ws/analysis` message type (see `02_analysis_and_decision.md` for the full list) — this is the single place that translates WS messages into `dispatch()` calls and local `setState` calls. A new WS message type needs a new `case` here.
- **`src/api/paAgentWs.ts`** — the three WS hooks (`useKlineSocket`, `useAnalysisSocket`, `useChatSocket`), each independently epoch-tagged and independently reconnecting with backoff.

## 2. The `.app-shell` Layout-Budget History — Read Before Adding Any New Stacked Block

`.app-shell` is a flex-column container holding (top to bottom, in the order phases added them): `Toolbar`, `.main-layout` (chart + side-pane: decision panel/future-trend/decision-tree text), `.flow-row` (phase 4, 480px, the decision-flow diagram), `.chat-debug-row` (phase 5, ~420px, chat panel + debug panel).

- **Phase 1–3**: `.app-shell` was `height: 100vh` (fixed). This worked because total content height happened to stay under one screen.
- **Phase 5's regression**: adding `.chat-debug-row` pushed total height past `100vh`. Because the container's height was *fixed*, flex children got force-compressed rather than the page scrolling — compressed boxes still retained their content's natural minimum size, so content visually overflowed and covered adjacent blocks. This silently broke a **phase-3** e2e test (`test_decision_tree_path_row_click_highlights_full_tree_node`, a click got intercepted by the now-overlapping `.flow-row`) — a test phase 5 itself never touches or thinks to re-run, because phase 5's own new e2e scenarios don't exercise that click path.
- **The fix** (still in effect as of phase 7): `.app-shell` changed to `min-height: 100vh` (page scrolls vertically when content exceeds one screen — an accepted, permanent design, not a temporary state), plus `flex-shrink: 0` on `.flow-row`/`.chat-debug-row` and `min-height: 480px` on `.main-layout` so the chart area can't be over-compressed on narrow viewports.
- **The lesson, stated as a rule**: **before adding another stacked block to the dark workbench, run the entire Playwright e2e suite (not just your new scenario) before considering the change done.** A regression in an unrelated earlier phase's test is exactly the kind of thing that a scoped "did my new stuff pass" check will miss — this is why `docs/webui_migration/phase-5-completion-report.md` and `phase-6-completion-report.md` both independently arrived at "run the full suite, not just the new file" as a lesson (see `09_testing_and_pitfalls.md`).
- Phase 6 and 7 both **avoided adding a new stacked block entirely** rather than risk repeating this: phase 6's demo controls went into the existing `Toolbar` (reusing a phase-5 placeholder button's position), and phase 7's wait-for-close/resume-chart controls did the same. **Prefer extending an existing row/toolbar over adding a new one, when the feature is toolbar-shaped** (a control, not a data panel).

## 3. No Global Settings-Invalidation Mechanism (a known architectural gap)

Components that read settings once on mount (e.g. `DecisionFlowPanel` reading `general` settings — see `03_decision_tree_and_flow.md`) do **not** react to `SettingsModal` saving a change — there is no pub/sub or query-invalidation layer connecting "a setting was saved" to "already-mounted components should refetch." If a feature genuinely needs this (hot-reload a setting into a live component), it doesn't exist yet and would need to be built, not assumed.

## 4. Also Check

- `01_kline_and_chart.md`, `02_analysis_and_decision.md`, `03_decision_tree_and_flow.md`, `04_chat_and_debug.md` — each panel `App.tsx` mounts and the state each one needs threaded through.
- `09_testing_and_pitfalls.md` — the "run full e2e, not just new scenarios" convention this section's history motivates.
