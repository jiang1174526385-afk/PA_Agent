# 02 — Analysis Submission and the Decision Panel

> Router: `docs/dev_guide/webui.md`. Read this doc for `/ws/analysis`, `AnalysisRunner`, `DecisionPanel.tsx`/`FutureTrendPanel.tsx`, the `stage2_decision` shape gotcha, and the trader-equation/win-rate/risk-reward display.

## 1. Architecture

- **Backend**: `pa_agent/webui/services/analysis_runner.py::AnalysisRunner` — asyncio equivalent of the desktop `pa_agent/gui/main_window.py::_AnalysisWorker` (a `QThread` wrapper over `TwoStageOrchestrator.submit`). Single-flight: only one analysis runs at a time; cancel is cooperative via a cancel token.
- **Route layer**: `pa_agent/webui/api/analysis.py::ws_analysis` — the one `/ws/analysis` endpoint handles three submit modes distinguished by an `active_mode` local: `mode: "full"`, `mode: "incremental"`, `mode: "demo"` (+ `demo_record_id`, see `05_demo_and_notify.md`). `cancel` routes to whichever runner (`AnalysisRunner` or `DemoRunner`) is currently active.
- **Client→server messages**: `{"type": "submit", "mode": "full" | "incremental" | "demo", "demo_record_id"?: string}`, `{"type": "cancel"}`.
- **Server→client message types** (all defined in `analysis_runner.py`/`analysis.py`, mirrored in `types/domain.ts::AnalysisWsInbound`): `event` (status text), `stage1_reasoning`/`stage1_content`/`stage2_reasoning`/`stage2_content` (streamed chunks), `stage_prompt` (system/user prompt text, feeds the debug panel), `stage2_files` (strategy files used), `record` (final `AnalysisRecord.model_dump()` + sibling `trade_metrics`, see §3), `error`, plus demo-only `demo_finished` and `order_opportunity` (see `05_demo_and_notify.md`).
- **`AnalysisRecord`** (`pa_agent/records/schema.py`) is the core, shared, Pydantic model — written to `records/pending/*.json` by the orchestrator, read by the desktop GUI, and sent verbatim (`.model_dump()`, no field stripping) over `/ws/analysis`. **Do not add web-display-only fields to this model** — it's core business logic's data contract, not a view model. Add derived/display fields as a **sibling** field in the WS message envelope instead (see §3's `trade_metrics` for the established pattern).

## 2. The `stage2_decision` Nested-vs-Flat Shape — Read Before Touching Either Panel

**This is a permanent reality, not a bug to eventually "finish fixing".** Real production `stage2_decision` (and `stage1_diagnosis`) are whatever JSON the AI model returned, validated but not restructured by `pa_agent/ai/json_validator.py` — in practice this means `stage2_decision` looks like:

```json
{"decision": {"order_type": "...", "entry_price": ..., "order_direction": "...", "estimated_win_rate": ...}, "decision_trace": [...], "gate_shortcircuited": false}
```

i.e. the actual order fields are nested one level under a `"decision"` key. But **every test fixture in this project since phase 1** (`tests/webui/conftest.py::_build_record`, `tests/webui/e2e/conftest.py::_build_record`) uses a **flat** shape — `order_type` etc. directly at the top level of `stage2_decision` — because that's simpler to hand-write for tests. Both shapes are real and both must keep working.

- **Backend normalization**: `pa_agent/webui/services/decision_shape.py::decision_inner(stage2_decision: dict | None) -> dict | None` — tries `.get("decision")`, falls back to treating the input as already-flat. Originally written inline in `order_alert.py` (phase 6), extracted to this shared module in phase 7 so `trade_metrics_view.py` doesn't duplicate it. **Import this function; do not write a third copy of the same unwrap logic.**
- **Frontend normalization**: `DecisionPanel.tsx` and `FutureTrendPanel.tsx` each do `const inner = (decision as MaybeNestedStageDecision)?.decision ?? decision;` right after the null-check, then read every field (`order_type`, `entry_price`, `next_bar_prediction`, etc.) from `inner`, never from the raw `decision` prop. **If you add a new field read to either component, read it from `inner`.** This was a real bug in production (phase-1-through-6 code read `decision.xxx` directly) that six phases of migration didn't catch because the test fixtures happened to be flat — fixed in phase 7. `decisionOverlay.ts` (the chart price-line overlay, see `01_kline_and_chart.md`) has the same requirement.
- `MaybeNestedStageDecision` (in `types/domain.ts`) is the type alias expressing "either shape" — `StageDecision & { decision?: StageDecision | null }`.

## 3. Trader Equation / Estimated Win Rate / Risk-Reward Display (phase 7)

Desktop reference: `pa_agent/gui/decision_panel.py` imports `compute_risk_reward`/`format_estimated_win_rate`/`max_risk_reward_ratio`/`min_risk_reward_ratio`/`passes_trader_equation` from `pa_agent/util/trade_metrics.py` (pure functions, no Qt dependency — import directly, never reimplement the math in TypeScript).

- **`pa_agent/webui/services/trade_metrics_view.py::build_trade_metrics(record: AnalysisRecord | None) -> dict | None`** — calls `decision_shape.decision_inner()` then the `trade_metrics.py` functions. Returns `None` when the record is empty, the decision can't be unwrapped, or `order_type == "不下单"`.
- Sent as a **sibling field to `record`**, not nested inside it, in every `{"type": "record", ...}` WS message (both `analysis_runner.py` and `demo_runner.py`):
  ```json
  {"type": "record", "record": {...AnalysisRecord.model_dump()...}, "trade_metrics": {
    "risk_reward_ratio": 2.5, "risk_reward_text": "2.50 : 1",
    "estimated_win_rate_pct": 65, "trader_equation_passed": true,
    "min_risk_reward_ratio": 1.0, "max_risk_reward_ratio": 1.0
  } | null}
  ```
- Frontend: `App.tsx` holds `tradeMetrics` state (set from `msg.trade_metrics` in the `"record"` case of `useAnalysisSocket`'s callback), passed as `<DecisionPanel decision={decision} tradeMetrics={tradeMetrics} />`. `DecisionPanel.tsx` renders 风险回报比/预估胜率/交易者方程 only when `tradeMetrics` is non-null (colors: `--success` when passed, `--danger` when failed, `--fg-2` for "—").
- Test coverage: `tests/webui/test_trade_metrics_view.py` (8 cases: nested shape, flat-fixture shape, `不下单` → null, missing win-rate → ratio present but `trader_equation_passed=null`, invalid geometry, `stage2_decision=None`); `DecisionPanel.test.tsx`/`FutureTrendPanel.test.tsx` cover both shapes end-to-end.

## 4. Data-Link Verification Note (from phase 3, still true)

`AnalysisRecord.stage1_diagnosis`/`stage2_decision` are typed `Optional[dict]` with **no nested Pydantic sub-model** — whatever JSON the AI returned (post-`json_validator.py` validation) flows through `AnalysisRunner`'s `record.model_dump()` unchanged. This means any field present in the AI's real JSON output (`gate_trace`, `decision_trace`, `terminal`, etc.) is already available over `/ws/analysis` with **zero runner/schema changes needed** — don't assume you need to modify `AnalysisRecord` or `AnalysisRunner` to expose a new AI-output field; verify first (as phase 3 did, with an explicit passthrough pytest assertion) before assuming a backend change is required.

## 5. Also Check

- `01_kline_and_chart.md` — submit gating on `hasFrame`, chart freeze happening inside the same submit handlers.
- `03_decision_tree_and_flow.md` — the same record's `gate_trace`/`decision_trace`/`terminal` fields, rendered by a different pair of components.
- `04_chat_and_debug.md` — `build_chat_session()` is rebuilt every time a new `record` arrives (inside `analysis.py::_run()`, mirroring the desktop's `_on_record_ready_impl`).
- `08_state_and_layout.md` — `App.tsx`'s full WS-message-routing switch statement.
