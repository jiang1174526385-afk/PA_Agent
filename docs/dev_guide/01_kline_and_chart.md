# 01 — K-line Streaming and Chart Rendering

> Router: `docs/dev_guide/webui.md`. Read this doc for anything touching data-source/symbol/timeframe selection, `/ws/kline`, the candlestick chart, decision price-line overlay, chart freeze/resume, or the wait-for-bar-close feature.

## 1. Architecture

- **Backend**: `pa_agent/webui/services/refresh_broadcaster.py::RefreshBroadcaster` — asyncio equivalent of the desktop `pa_agent/data/refresh_loop.py::RefreshLoop`. One instance owns one connected `DataSource` for the lifetime of a `(source, symbol, timeframe)` subscription; polls on an interval and fans the resulting `KlineFrame` out to every subscribed WebSocket. Backoff constants (`_BACKOFF_BASE_S=0.5`, `_MAX_BACKOFF_S=10.0`) are copied verbatim from `RefreshLoop` so retry cadence matches the desktop app.
- **Route layer**: `pa_agent/webui/api/kline.py` — REST `GET /api/data-sources`, `/api/symbols`, `/api/timeframes`, `/api/kline/snapshot` (one-shot fetch, used for instant first-paint before the WS frame arrives); WS `/ws/kline` (subscribe/frame/status/error messages, epoch-tagged).
- **Schema**: `pa_agent/webui/schemas/kline.py::KlineFrameOut.from_frame()` — the single place that converts `pa_agent/data/base.py::KlineFrame` (a frozen dataclass) into JSON. **Both the WS broadcast and the REST snapshot call this same method**, so any field added here reaches both paths automatically — don't add a second conversion path.
- **Frontend**: `src/chart/ChartView.tsx` (thin wrapper) + `src/chart/useLightweightChart.ts` (the actual `lightweight-charts` integration: candles + EMA20/ATR14 lines) + `src/chart/decisionOverlay.ts` (entry/TP1/TP2/SL horizontal price lines, computed from the current decision).
- **Data flow into the frontend**: `src/api/paAgentWs.ts::useKlineSocket` subscribes over `/ws/kline`, epoch-filters stale frames (a `subscribe` bumps an epoch counter; frames tagged with an older epoch are dropped — this project's WS reconnect model is stricter than the `tradingAgents/webui` reference architecture it was originally modeled on, which has no epoch filtering at all).

## 2. `KlineFrame.bars` Ordering — Read This Before Touching `is_forming`/Countdown Logic

**`frame.bars` (and thus `KlineFrameOut.bars`) is newest-first** — `bars[0]` is the forming/newest bar, `bars[-1]` is the oldest. Confirmed via `KlineFrame`'s own docstring in `pa_agent/data/base.py` and `pa_agent/data/snapshot.py`'s usage. `pa_agent/data/bar_close_wait.py::has_forming_bar_at_head()` expects this ordering and is called directly on `frame.bars` with no reversal needed.

## 3. Wait-for-Bar-Close (phase 7)

Desktop reference: `pa_agent/gui/main_window.py`'s "等待最新K线收盘后再提交分析" checkbox + countdown label (search `_wait_close_countdown_label`/`_arm_wait_for_bar_close`), backed by pure functions in `pa_agent/data/bar_close_wait.py`:
- `has_forming_bar_at_head(bars_newest_first, timeframe, now_ms=None, symbol=None) -> bool`
- `seconds_until_bar_closes(ts_open_ms, timeframe, now_ms=None) -> int | None`

Web equivalent: `KlineFrameOut` gained two fields, computed in `from_frame()` — **no new endpoint**, both `/ws/kline` (which ticks every `refresh_interval_ms`) and `GET /api/kline/snapshot` get these automatically:
- `is_forming: bool`
- `seconds_until_close: int | None` (only non-null when `is_forming` is true)

Frontend wiring lives in `App.tsx` (not in a dedicated hook — kept inline since the logic is small):
- `Toolbar.tsx` renders a "等待收盘" checkbox + (when armed) a `[data-testid="wait-close-countdown"]` label, and (when frozen — see §4) a `[data-testid="resume-chart-button"]` button.
- `App.tsx` state: `waitForClose`, `pendingSubmitMode: "full" | "incremental" | null`. Clicking submit/incremental while `waitForClose && kline.frame?.is_forming` arms `pendingSubmitMode` instead of submitting immediately. A `useEffect` watching `kline.frame` fires the deferred submit the moment `is_forming` flips to `false`. Unchecking the checkbox clears `pendingSubmitMode` (mirrors desktop "取消勾选复选框 → 取消等待"). Switching source/symbol/timeframe also clears it (`resetWaitAndFreezeState()`).

**Known test-coverage gap**: the e2e scenario (`tests/webui/e2e/test_phase7_gap_fixes_smoke.py::test_wait_for_close_checkbox_arms_countdown_and_uncheck_cancels`) only verifies "arm → countdown appears → uncheck → countdown disappears" — it does **not** wait for a real 15-minute OKX bar to actually close and auto-submit (too slow for a test). That final leg is covered only by the `is_forming`/`seconds_until_close` unit tests in `tests/webui/test_kline_api.py` plus manual code review. If you suspect a bug in the auto-submit trigger itself, consider a short custom test timeframe rather than trusting this note as proof it works end-to-end.

## 4. Chart Freeze-on-Submit + Manual Resume (phase 7)

Desktop reference: `pa_agent/gui/main_window.py`'s chart-freeze-during-analysis behavior (see `docs/图表K线与分析快照说明.md` for the full rationale — the chart must show exactly what was sent to the AI, so it freezes on submit and a "图表实时更新" button resumes live updates). This was a genuine gap that six earlier migration phases didn't track — closed in phase 7.

Web implementation is entirely frontend (no backend change): `App.tsx` state `chartFrozen: boolean` + `frozenFrame: KlineFrame | null`. `freezeChartNow()` snapshots `kline.frame ?? snapshotFrame` and is called at the top of every submit path (`submitFullNow`, `submitIncrementalNow`, `handlePlayDemo`). `ChartView`'s `frame` prop becomes `chartFrozen ? frozenFrame : (kline.frame ?? snapshotFrame)`. `handleResumeChart()` clears both. Switching source/symbol/timeframe also clears both (`resetWaitAndFreezeState()`), matching the desktop's "切换品种/周期时,图表自动重置".

## 5. Decision Price-Line Overlay

`src/chart/decisionOverlay.ts` draws entry (white solid), stop-loss (red dashed), TP1 (green dashed), TP2 (light-green dashed) horizontal lines once a decision exists — mirrors the desktop's `pa_agent/gui/chart_decision_overlay.py`. Reads from the **normalized** decision shape (see `02_analysis_and_decision.md`'s nested-vs-flat note) — if you're adding a new price-derived overlay, make sure you're reading `inner`, not the raw `decision` prop, same pitfall as `DecisionPanel.tsx`.

## 6. Historical Pitfalls

- **`/ws/kline` frames containing `NaN` crash the browser's `JSON.parse`**: EMA20/ATR14 warm-up-period values are Python `float('nan')`; `_nan_to_none()` in `schemas/kline.py` converts them to `null` before serialization — frontend types already model these as `(number | null)[]`. If you add a new indicator, remember this conversion step.
- **Default data source must not be `mt5`**: `MetaTrader5` is Windows-only; a default of `"mt5"` makes the page fire a guaranteed-500 request on load in any non-Windows/non-MT5-logged-in environment (including this sandbox and CI). `defaultAppState.source` is intentionally `""` with a "选择数据源" placeholder forcing an explicit user choice.
- **"提交分析" must gate on an actual `/ws/kline` frame having arrived, not just on symbol/timeframe being selected**: the REST snapshot renders the chart faster than the WS broadcaster's first frame, but `/ws/analysis` checks the broadcaster's internal `latest_frame`, not what's on screen. `Toolbar`'s `hasFrame` prop (driven by `kline.frame !== null`) is the actual submit gate.
