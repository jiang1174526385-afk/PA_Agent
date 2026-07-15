# 03 — Decision Tree Replay and Animated Decision Flow

> Router: `docs/dev_guide/webui.md`. Read this doc for the "决策树" text-replay tab, the "决策树可视化" animated diagram tab, and their shared `/api/decision-tree/*` backend.

## 1. Architecture

- **Backend module reused**: `pa_agent/ai/decision_tree.py` — pure functions, no Qt dependency: `merge_traces`, `format_trace_answer`, `normalize_bar_range`, `format_bar_basis_suffix`, `plain_trace_question`, `get_node_branch_outcome`, `load_decision_tree()` (the static tree definition, `@lru_cache`d), `_BRANCH_DISPLAY_ZH`. **Import and call these — the formatting/business-rule logic belongs in this module, not reimplemented in TypeScript.** This project's stable division of labor: *domain formatting → backend, pixel/geometry layout → frontend.*
- **Route layer**: `pa_agent/webui/api/decision_tree.py` — three stateless, side-effect-free endpoints:
  - `GET /api/decision-tree/static` → the static tree structure (`DecisionTreeStaticResponse`), fetched once by the frontend.
  - `POST /api/decision-tree/replay` → given trace data, returns formatted table rows (`DecisionTreeReplayRow`: stringified `answer_display`/`basis`/`reason_display`) for the **text replay** tab.
  - `POST /api/decision-tree/flow` (phase 4) → given the same request body, returns the finer-grained fields the **flow diagram** needs (`branch`/`skipped`/`side`/`overridden`/`program_answer`, plus `alt`/`terminal`/`band_before` structures) — a **separate** endpoint from `/replay`, not an extension of it, because `DecisionTreeReplayRow` is a "table row" shape that can't carry both without becoming a leaky two-purpose DTO.
- **Frontend — text replay**: `src/decisionTree/DecisionTreePanel.tsx` + `decisionTreeApi.ts`. Terminal-outcome banner + path-replay table + full static tree (`<details>` collapse, open only for sections containing a visited node — a deliberate deviation from the desktop's "sections 1–2 always open" rule, see §3). Clicking a path-table row highlights + scrolls to the corresponding tree node (`data-node-id` + ref map + `scrollIntoView`, mirroring desktop `_on_path_row_selected`/`_scroll_tree_to_node`).
- **Frontend — animated flow**: `src/decisionFlow/DecisionFlowPanel.tsx` + `layout.ts` (pure geometry, unit-tested in `layout.test.ts`) + `nodes.tsx` (React Flow node components) + `decisionFlowApi.ts`. Built on **`@xyflow/react`** (`react-flow`, peer-dep `react>=17`, no conflict with this project's React 19).
- **Colors**: backend returns semantic `color_key` values (`success`/`danger`/`warning`/`muted`/`secondary`), not hex — frontend maps these to the dark theme's existing `var(--success)` etc. CSS variables. Don't have the backend return hex colors; don't invent new hex values in the frontend either (see `webui.md` §1.2's theme-isolation rule).

## 2. Flow-Diagram Specifics (`DecisionFlowPanel.tsx`)

Desktop reference: `pa_agent/gui/decision_flow_viz.py` (~1215 lines, `QGraphicsView`/`QGraphicsScene`). Full read required before touching this area — it's the single largest/most complex file this migration ported.

- **Node types**: `flowDecision`/`flowAlt`/`flowTerminal` (mirroring the desktop's decision/alt/terminal node kinds) + `flowBand` (phase-separator band, also a distinct item on the desktop side).
- **Edges via named handles, not raw coordinates**: each decision card exposes `left`/`right`/`bottom` source handles + one `top` target handle; `react-flow` computes the path. This (not hand-rolled SVG bezier) is what lets the "connection flowing dot" animation just be `react-flow`'s built-in `animated` edge property — no custom animation clock needed.
- **`_taken_branch_side` is NOT importable** — it's a private function physically inside `pa_agent/gui/decision_flow_viz.py` (a GUI file), even though its logic itself has no Qt dependency. It was re-implemented (6 lines, docstring says "mirrors...") in `pa_agent/webui/api/decision_tree.py` rather than imported. If you need similarly-shaped logic that lives inside a GUI file (not a shared `pa_agent/ai/`-style module), check whether it's small/pure enough to re-express locally with a "mirrors X" docstring, same pattern.
- **Autoplay**: reads `GeneralRead.decision_flow_auto_play`/`decision_flow_play_seconds` (both exist since phase 1's settings schema; first *consumed* by phase 4). Camera movement is **node-to-node `setCenter(x, y, {duration})` easing**, not the desktop's continuous 40ms-tick interpolation along a dense path — a deliberate simplification (§0.2 decision in phase 4), confirmed with the user. If this visual difference ever needs fixing to match the desktop's "flying" look, it requires a `requestAnimationFrame`-driven tween loop replacing the current `setCenter` calls — not yet built.
- **Settings changes don't hot-reload into an already-mounted `DecisionFlowPanel`**: it fetches `general` settings once on mount, doesn't listen for `SettingsModal`'s save event. There is **no global settings invalidation mechanism** in this project's frontend architecture — if you build a feature needing "change a setting → already-mounted components react immediately," you'll need to introduce one (doesn't exist yet as of phase 7).
- **Fullscreen** ("全屏推演"): CSS `position: fixed` overlay toggle, not a separate window — simplest-possible parity with the desktop's dedicated dialog.
- **Node sizing**: ~55% of desktop pixel dimensions (`NODE_W=320` vs desktop `580`), same aspect ratios/spacing ratios, because the web panel is a fixed 480px-tall in-page region (`.flow-row`), not an infinite zoomable canvas.
- **`color-mix(in srgb, var(--flow-accent) N%, transparent)`** is how runtime-injected accent colors (a CSS custom property, not a compile-time-known hex string) get semi-transparent variants — string-concatenating an alpha suffix onto a `var(...)` reference doesn't work. Reuse this pattern for any other "runtime-decided accent + translucent glow/background" need.

## 3. Historical/Deliberate Deviations from Desktop Behavior

- Text-replay tab's full-tree default-expand rule: **"expand only sections containing a visited node"** (web) vs desktop's **"sections with `id <= 2` always expand regardless"**. Not settled as definitely-correct — flagged in the phase-3 report as an implementation-time judgment call; ask the user if strict desktop parity turns out to matter.
- `selectedNodeId` (path-row highlight state) is **not reset** when a new analysis record arrives — after a second submission, a stale highlight can point at a node id that doesn't exist in the new trace (silently renders as "nothing highlighted", no crash). Known low-priority issue, never fixed across phases 3–7.

## 4. Also Check

- `02_analysis_and_decision.md` — the source `AnalysisRecord`'s `gate_trace`/`decision_trace`/`terminal` fields these two panels consume (same record, no additional fetch needed for text replay/flow — both are computed from the record already held in `App.tsx`'s state, via the two POST endpoints above).
- `07_settings_and_config.md` — the three `decision_flow_*` settings.
- `08_state_and_layout.md` — `.flow-row`'s place in the `.app-shell` vertical layout budget (480px, part of why later phases had to change `.app-shell` from fixed to `min-height`).
