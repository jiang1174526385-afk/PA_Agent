# 06 — Trade-Record Analysis Report Page (`/reports`)

> Router: `docs/dev_guide/webui.md`. Read this doc for the `/reports` page — KPI cards, equity/monthly/calendar/distribution charts, the order table, and the MT5/OKX backfill pipeline.

## 1. This Page Is Intentionally Isolated — Read Before Touching Shared Files

`/reports` is a **net-new feature with no desktop-GUI equivalent** (not a migration of any existing panel), built from a design mock (`qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg`, repo-root `qunyou/`, **not** under `pa_agent/` despite what older docs/plans may say). It deliberately:

- Uses a **separate light card-dashboard theme** — `src/reportStyles/reportTokens.css` (all `--report-*` custom properties), which does **not** import the dark workbench's `tokens.css`. Do not make this page share theme variables with the rest of the app, and do not let its light-theme choices bleed into `tokens.css`/`app.css`. See `webui.md` §1.2.
- Uses **`recharts`** for all its charts (equity curve, monthly returns, symbol-distribution donut, PnL calendar heatmap, trade-overview donut, direction-analysis donuts, PnL-overview donut, holding-time histogram, slippage histogram) — a separate charting library from the dark workbench's `lightweight-charts` (which only renders K-line candles). The two don't conflict; don't try to unify them.
- Is routed via `main.tsx`'s plain `pathname` check (`"/"` → dark workbench, `"/reports"` → this page) — **no `react-router`** is used anywhere in this project. Don't introduce one just for this page.

## 2. Backend

- **`pa_agent/data/trade_history.py`** — read-only MT5/OKX historical-fill queries: `fetch_mt5_deals()` (wraps `MetaTrader5.history_deals_get`, field names from official docs), `fetch_okx_positions_history()` (OKX's `positions-history` endpoint, field names from official docs). **Neither has ever been run against a real account/credentials** — implemented strictly from API documentation, a standing verification gap (flag this if you're asked to debug a real-account backfill result that looks wrong; the docs-vs-actual-response mismatch risk is real, e.g. `tradingAgents/webui/terminal/okx_rest.py`'s own comment about `positions-history` pagination-cursor direction being under-documented).
- **`pa_agent/records/trade_fill_backfill.py::backfill_csv()`** — idempotent matching of AI-decision CSV rows against real fills, purely additive columns (`fill_status`/`actual_entry_price`/`actual_exit_price`/`filled_at`/`closed_at`/`pnl_usd`/`pnl_pips`/`holding_duration_s`/`win_loss`/`match_confidence`). Matching window per CSV row = `[this row's record_time, next row's record_time)`, last row capped at `min(now, record_time + 30 days)` (`_MAX_LOOKAHEAD_DAYS` constant) — this is a considered choice (CSV rows are "one decision replaces the previous plan," so the next row is a natural right boundary; 30 days bounds the otherwise-unbounded last-row lookup), not an arbitrary number — read the phase-2 report before changing it.
- **`match_confidence` is a two-state field (`matched`/`unmatched`)**, not the three-state `exact`/`fuzzy`/`unmatched` the original execution plan sketched — confirmed simplification with the user (no price-tolerance-tiered matching).
- **`pa_agent/records/report_metrics.py`** — pure functions computing every KPI/chart's data (total P&L, max drawdown as `drawdown_amount / peak_equity_before_that_drawdown` — **not** relative to a starting-capital figure, since none of MT5/CSV/OKX carries one; profit factor; win rate incl. long/short split; avg trade; trade count; max consecutive losses; stagnation days; holding-time buckets; slippage buckets; equity curve; monthly returns; symbol distribution; PnL calendar). Formulas are documented as docstrings/comments next to each function — read there for exact definitions, don't infer from the frontend.
- **Route layer**: `pa_agent/webui/api/reports.py` — `GET /api/reports`, `POST /api/reports/{key}/backfill`, `GET /api/reports/{key}/summary`, `GET /api/reports/{key}/calendar?year=&month=` (a fourth endpoint added beyond the original plan, because the PnL-calendar month-pagination need doesn't fit cleanly into `summary`'s response), `GET /api/reports/{key}/orders`.
- **Return-rate / annualized-return KPIs do not exist** — confirmed with the user (phase 2): CSV/MT5/OKX have no starting-capital or historical-balance figure, and fabricating one would mislead. The KPI row is 8 cards (total P&L, max drawdown, profit factor, win rate, avg trade, trade count, max consecutive losses, stagnation days), not the design mock's 9 (which included a return-rate card).
- **`order_direction`'s canonical Chinese values are "做多"/"做空"**, not "多头"/"空头" — authoritative source is `pa_agent/ai/prompts/schemas.py`/`json_validator.py`. `_is_long()`-style direction checks in this module and `trade_fill_backfill.py` each have their own lightweight copy (not yet extracted to a shared `pa_agent/util/` helper since only two call sites exist — extract if a third appears).

## 3. Frontend

- `src/reports/ReportsPage.tsx` (top-level layout: breadcrumb, date-range picker, strategy filter, "管理报告" button) + `SideNav.tsx` (vertical icon nav: 总览/报告对比/收益分析/风险分析/策略分析/设置 — only 总览 has real content, the other four are `"开发中"` placeholders, per confirmed phase-2 scope) + `KpiCard.tsx` + `OrderTable.tsx` (search/sort/filter/export/pagination) + `charts/*.tsx` (9 components, one per chart type listed in §1) + `format.ts` (formatting helpers, unit-tested).
- **Strategy filter dropdown is a hardcoded `decision_stance` enum** (`conservative`/`balanced`/`aggressive`/`extreme_aggressive`), not values discovered from the actual CSV — a strategy label outside this enum (e.g. from a manually-edited CSV) won't appear as a filter option.
- **Unresolved ambiguity, never confirmed**: the design mock has what look like two separate top dropdowns; this implementation treats them as one duplicate-looking filter and built only one "策略" dropdown. If the intended meaning was actually "account selector" + "strategy filter" as two independent concepts, an account/account-id dimension filter is still entirely unbuilt.

## 4. Historical Pitfalls

- **`formatUsd`'s negative-number sign placement**: `${value.toLocaleString(...)}` already prepends `-` for negative numbers — don't also prepend a `sign` variable, or you get `$-10,772.10` instead of `-$10,772.10`. Take the absolute value for the numeric part, prepend the sign before the `$` separately.
- **`recharts`' `Tooltip formatter` callback type doesn't accept an explicit `(value: number) => ...` annotation** — its `ValueType` is `number | string | Array<...> | undefined`; let TS infer the parameter type from `recharts`' own `Formatter` type and do `Number(value)` inside the function body instead.
- **No dedicated test for "extra CSV columns don't break older reader code"** — relies on `csv.DictWriter(..., extrasaction="ignore")` + `csv.DictReader`'s natural column-name-based reads. Judged low-risk but never explicitly tested; still an open item if you're asked to harden CSV forward-compat.

## 5. Also Check

- `07_settings_and_config.md` — the OKX credentials tab (`api_key`/`api_secret`/`passphrase`) this page's backfill needs.
- Nothing else — this page has no other real dependency on the dark-workbench code, by design.
