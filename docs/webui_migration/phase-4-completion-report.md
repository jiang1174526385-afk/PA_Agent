# 阶段四总结报告：动画流程图可视化（DecisionFlowViz）

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-4-execution-plan.md`](phase-4-execution-plan.md)
> 上一阶段总结：[`phase-3-completion-report.md`](phase-3-completion-report.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

## 0. §0 三个决策问题的确认结果

实施前已征得您确认（会话内 AskUserQuestion，60 秒无响应后二次确认，您明确答复）：

1. **渲染方案**：`react-flow`（`@xyflow/react@^12.11.2`，React ≥17 兼容，与本项目 React 19 无冲突）。
2. **动画保真度**：简化版——CSS 驱动的节点高亮/连线流动光点（`animated` 边）/终点呼吸光晕，不做角标装饰、双色网格背景、扫描线等桌面端 QPainter 逐帧特效。
3. **自动播放**：本阶段一起实现，读取既有 `GeneralRead.decision_flow_auto_play`/`decision_flow_play_seconds` 设置。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §3.3 完整通读 `decision_flow_viz.py`（1215 行） | ✅ | 会话内一次性通读全文，梳理出节点类型/布局算法/双定时器动画/交互模型，见 §4 |
| §5.1 节点数据模型（decision/alt/terminal 三类，含存根/终点尺寸差异） | ✅ | Web 端保留三类节点语义（`flowDecision`/`flowAlt`/`flowTerminal`），新增 `flowBand`（阶段分隔带，桌面端也是独立 `_PhaseBandItem`） |
| §5.2 渲染技术栈选型与依赖评估 | ✅ | `@xyflow/react` peerDeps `react/react-dom >=17`，与项目 React 19 无冲突，构建产物增量 ~182KB（804KB→986KB，未压缩），与阶段二 `recharts` 先例一致，已如实记录 |
| §5.3 节点/边 JSON 数据模型设计 | ✅ | 新增 `POST /api/decision-tree/flow`，复用阶段三确立的模式（格式化逻辑留在后端 `pa_agent/ai/decision_tree.py` 的纯函数，前端只做布局几何），见 §2 |
| §5.4 前端组件 `src/decisionFlow/` | ✅ | `DecisionFlowPanel.tsx`/`layout.ts`/`nodes.tsx`/`decisionFlowApi.ts`，沿用阶段一 `tokens.css` 暗色主题变量，未新增色值（详见 §5 设计决策） |
| §5.5 动画方案（简化版） | ✅ | 节点悬停发光（CSS `box-shadow`）、连线流动光点（`react-flow` 内置 `animated` 边 dash 动画）、终点呼吸光晕（CSS `@keyframes` 脉冲），见 §4 |
| §5.6 自动播放 | ✅ | `DecisionFlowPanel` 读取 `GeneralRead.decision_flow_auto_play`/`decision_flow_play_seconds`，新流程图加载后按序 `setCenter` 飞跃决策路径各节点，点击画面可中断（对应桌面 `eventFilter` 点击取消） |
| 全屏推演 | ✅（增量，见 §5） | CSS class 切换全屏覆盖层，功能对齐桌面端「全屏推演」按钮，非新增交互范畴之外的功能 |
| 后端 pytest | ✅ | `tests/webui/test_decision_tree_api.py` 新增 2 用例（`test_flow_left_right_down_branch_sides_and_alt_outcomes`/`test_flow_empty_traces_returns_no_path`） |
| 前端 tsc/vitest/build | ✅ | 见 §6；新增 `src/decisionFlow/layout.test.ts`（3 用例，覆盖左右分支镜像布局/跳过直连/阶段带间距） |
| Playwright e2e | ✅ | `tests/webui/e2e/test_phase4_decision_flow_smoke.py`（3 场景：节点+终点渲染、自动播放运行且无控制台错误、全屏切换） |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段五执行方案 | ✅ | [`phase-5-execution-plan.md`](phase-5-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增：**
- `pa_agent/webui/frontend/src/decisionFlow/DecisionFlowPanel.tsx`
- `pa_agent/webui/frontend/src/decisionFlow/layout.ts`
- `pa_agent/webui/frontend/src/decisionFlow/layout.test.ts`
- `pa_agent/webui/frontend/src/decisionFlow/nodes.tsx`
- `pa_agent/webui/frontend/src/decisionFlow/decisionFlowApi.ts`
- `tests/webui/e2e/test_phase4_decision_flow_smoke.py`

**修改：**
- `pa_agent/webui/schemas/decision_tree.py`（新增 `DecisionFlowAlt`/`DecisionFlowStep`/`DecisionFlowTerminal`/`DecisionFlowResponse`，未删除/重命名阶段三已有 DTO）
- `pa_agent/webui/api/decision_tree.py`（新增 `POST /decision-tree/flow` 端点 + `_taken_branch_side` 辅助函数 + `_OUTCOME_COLOR_KEY` 常量；阶段三的 `/decision-tree/static`、`/decision-tree/replay` 零改动）
- `pa_agent/webui/frontend/src/types/domain.ts`（新增 `DecisionFlowAlt`/`DecisionFlowStep`/`DecisionFlowTerminal`/`DecisionFlowResponse`）
- `pa_agent/webui/frontend/src/App.tsx`（挂载 `<DecisionFlowPanel record={state.record} />` 到主布局下方独立一行 `.flow-row`，未改动阶段一 `ChartView`/`side-pane` 既有布局结构）
- `pa_agent/webui/frontend/src/styles/app.css`（新增 `.flow-row`/`.decision-flow-*`/`.flow-*` 系列类，均使用 `tokens.css` 已有变量，未新增色值）
- `pa_agent/webui/frontend/package.json`/`package-lock.json`（新增依赖 `@xyflow/react@^12.11.2`）
- `tests/webui/test_decision_tree_api.py`（新增 2 条 `/decision-tree/flow` 用例，阶段三既有 4 条用例零改动）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 全部零改动（`git status --short -- pa_agent/gui/` 确认为空）。
- `pa_agent/ai/decision_tree.py` 零改动，仅被新端点 `import` 调用（`merge_traces`/`format_trace_answer`/`plain_trace_question`/`get_node_branch_outcome`/`_BRANCH_DISPLAY_ZH`）。
- 阶段二报告页面（`src/reports/`、`src/reportStyles/`）零改动。
- 阶段三决策树表格/树面板（`src/decisionTree/`、`/decision-tree/static`、`/decision-tree/replay`）零改动。

## 3. 遇到的问题、根因与解决方式

1. **`_taken_branch_side` 是桌面端 GUI 模块的私有函数，无法直接复用**：与 `merge_traces`/`format_trace_answer` 等不同，`_taken_branch_side` 定义在 `pa_agent/gui/decision_flow_viz.py` 内部（依赖 PyQt 无关但物理上在 GUI 文件里），Web 后端无法 `import`。逻辑本身只有 6 行且完全基于已可复用的 `format_trace_answer` 输出，因此在 `pa_agent/webui/api/decision_tree.py` 内按原样重新实现了一份（docstring 注明"mirrors ... "），未改动 `pa_agent/ai/decision_tree.py`。这是执行方案 §5.3 允许的"最小必要增量"，不是重复实现核心业务逻辑（`_taken_branch_side` 是纯展示层的分支路由判定，不涉及 AI 决策语义）。
2. **边（edge）的几何模型：raw 坐标点 vs react-flow 的 handle 连接**：桌面端 `_BranchEdge` 直接用场景坐标点画贝塞尔曲线；`react-flow` 的标准做法是节点间通过命名 handle（source/target）连接，由库自动计算路径。选择了后者（每个决策卡片有 `left`/`right`/`bottom` 三个 source handle + 一个 `top` target handle），而不是自己实现点对点 SVG 路径——这样可以直接使用 `react-flow` 内置的 `animated` 边属性做"连线流动光点"效果（对应 §0.2 简化版动画决策），避免重新实现动画时钟。
3. **自动播放的相机运镜简化**：桌面端 `_build_playback_path` 生成密集插值点，每 40ms 用 `centerOn` 平移一次相机，逐帧驱动。Web 端改为"逐节点跳跃"：每个决策/终点节点用 `react-flow` 的 `setCenter(x, y, {duration})` 做一次平滑过渡，总时长仍受 `decision_flow_play_seconds` 控制，按节点数均分。这比逐帧插值更符合 §0.2 的"简化版"决策，也避免了在 React 组件里维护一个独立的 40ms tick 定时器；副作用是运镜节奏是"节点到节点"的分段缓动而非桌面端的匀速直线平移，视觉上更像"跳转"而非"飞行"，如果您认为需要更平滑的连续插值，需要额外实施工作量（见 §8 遗留问题）。
4. **`decision_flow_auto_play` 默认值为 `True`**（`pa_agent/config/settings.py:72`），e2e 测试如果不干预会等待真实 50 秒（`decision_flow_play_seconds` 默认值）播放完成。测试内通过 `PUT /api/settings/general` 直接把 `decision_flow_play_seconds` 改小（2 秒）后再 `page.goto`，避免测试变慢，同时仍然验证了"自动播放确实被触发"这一行为契约。

## 4. 可复用经验与后续注意事项

- **几何计算放前端、领域格式化放后端，是本项目目前的稳定分工模式**：阶段三和阶段四都遵循"后端只输出已格式化的语义数据（颜色 key、分支方向、未走分支文案），几何/像素计算完全交给前端"这一原则。后续阶段（五：自由对话）如果出现类似"要不要新增端点"的问题，建议延续这个判断标准：格式化/业务规则 → 后端；纯展示布局 → 前端。
- **`react-flow` 的 `Handle` 需要显式 `id`，且同一节点可以有多个同类型（source）handle**：`FlowDecisionNode` 用 3 个 `source` handle（`left`/`right`/`bottom`，全部视觉上隐藏 `opacity:0`，仅用于连线锚点）实现了桌面端 `port_left`/`port_right`/`port_bottom` 的等价物。这是复用 `react-flow` 内置路径计算（而非手写 SVG bezier）的关键技巧，后续如果还要做其他分支型可视化，可以直接复用这个模式。
- **`color-mix(in srgb, ...)` 用于半透明色阶**：由于节点强调色是运行时通过 CSS 自定义属性（`--flow-accent`）注入的（不是编译期已知的十六进制字符串），无法用字符串拼接生成半透明变体（`${accent}55` 对 `var(--x)` 无效）。改用 `color-mix(in srgb, var(--flow-accent) N%, transparent)`，现代 Chromium（Playwright 测试用）与主流浏览器均支持。这个技巧比"每个语义色再定义一份透明版本变量"更省心，后续阶段如果也需要"运行时决定强调色 + 半透明背景/光晕"的场景，可以复用同一模式。
- **e2e 里改设置要绕开 UI 表单的时序问题**：`DecisionFlowPanel` 只在组件挂载时 fetch 一次 `general` 设置（不监听 `SettingsModal` 的保存事件），如果 e2e 想验证"改了设置后生效"，必须在 `page.goto()` 之前就把设置改好（通过 `PUT /api/settings/general` 直连后端），而不是"打开设置弹窗 → 改 → 保存 → 断言"这种更贴近用户操作但会因为没有跨组件的设置失效通知机制而拿不到预期效果的写法。这是本阶段发现的一个可能影响阶段五/六的小陷阱：如果后续阶段也有"设置面板改动需要立刻影响已挂载组件"的需求，需要引入某种全局设置 store/失效机制，目前架构里没有。

## 5. 设计决策与偏离原计划的原因

- **新增 `POST /api/decision-tree/flow` 而非扩展 `/decision-tree/replay`**：执行方案 §5.3 建议"评估是扩展现有响应，还是新建端点"。`replay` 的 `DecisionTreeReplayRow` 是"表格行"模型（一个字符串化的 `answer_display`/`basis`/`reason_display`），而流程图需要更细粒度的原始字段（`branch`/`skipped`/`side`/`overridden`/`program_answer` 等分别取用，还需要额外的 `alt`/`terminal`/`band_before` 结构），把两者塞进同一个响应会让 `DecisionTreeReplayRow` 承担两种不兼容的用途。选择新建端点，复用同一个请求体 `DecisionTreeReplayRequest`（未新增/未修改该请求模型），符合执行方案"新增字段，不删除/不重命名阶段三已有字段"的兼容策略。
- **新增全屏推演按钮**：执行方案 §2 非目标写"不在本阶段引入自动播放之外的额外交互"，但全屏是桌面端既有功能（`_open_fullscreen`），且总纲 §8 最终验收要求"功能对齐现有 PyQt6 GUI 全部面板"。判断这不属于"额外交互"而是功能对齐的一部分，用最简单的 CSS `position:fixed` 覆盖层实现（不是桌面端的独立 `QDialog` 子窗口），如果您认为这超出了阶段边界，可以要求回退，改动范围很小（`DecisionFlowPanel.tsx` 的 `fullscreen` state + `app.css` 的 `.fullscreen` 类）。
- **阶段带（band）使用 `var(--accent)`（teal）而非桌面端的 `_NEON_VIOLET`**：`tokens.css` 现有变量集里没有紫色调，按总纲 §2.1/阶段三先例（"均在阶段一暗色主题变量体系内，未新增色值"）的要求，没有新增十六进制色值，改用已有的 `--accent`（与决策节点默认强调色 `--accent-3` 视觉上可区分）。
- **节点卡片尺寸缩小为桌面端的约 55%**（`NODE_W=320` vs 桌面 `580`，其余同比例缩放）：桌面端 `QGraphicsScene` 是可自由缩放的无限画布，Web 端 `.decision-flow-panel` 是页面内固定 480px 高的区域，按桌面原尺寸会导致单个节点就撑满可视区域。保持了桌面端的比例关系（宽高比、级间距/节点宽度比、存根/终点相对尺寸），只是整体缩小，配合 `react-flow` 的 `fitView` 自动适配。

## 6. 实际运行的验证命令与结果

### 6.1 后端 pytest（含阶段一/二/三回归）
```bash
./.venv/bin/pytest tests/webui/ tests/unit/test_trade_fill_backfill.py --browser chromium -q
# 60 passed（exit code 0，无失败/无跳过）
```
覆盖：阶段一 `test_kline_api.py`/`test_analysis_ws.py`/`test_settings_api.py`/`e2e/test_phase1_smoke.py` 全部仍通过；阶段二 `test_reports_api.py`/`test_trade_fill_backfill.py`/`e2e/test_phase2_reports_smoke.py` 全部仍通过；阶段三 `test_decision_tree_api.py`（原 4 条）/`e2e/test_phase3_decision_tree_smoke.py` 全部仍通过；阶段四新增 `test_decision_tree_api.py`（+2 条 `/decision-tree/flow` 用例）/`e2e/test_phase4_decision_flow_smoke.py`（3 条）。

### 6.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 4 passed (4) / Tests 24 passed (24)（本阶段新增 layout.test.ts 3 条）
npm run build             # 构建成功；产物 986.55 kB（未压缩前，阶段三为 804KB，新增 @xyflow/react 依赖导致体积增长约 182KB），仍有 "chunk > 500KB" 警告（未做代码分割，沿用阶段二/三既有模式，未在本阶段引入新的构建配置）
```

## 7. 数据/兼容性迁移情况

- 无数据迁移：本阶段不写入/修改任何持久化数据，只读取 `/ws/analysis` 已推送的 record 数据（经由已有的 `gate_trace`/`decision_trace`/`terminal` 字段）并在新端点里重新格式化展示。
- 新增端点无状态、无副作用（`POST /decision-tree/flow` 是纯函数式转换，不落盘，不修改 `pa_agent/ai/decision_tree.py` 或 `AnalysisRecord`）。
- `GeneralRead.decision_flow_auto_play`/`decision_flow_play_seconds`/`decision_flow_default_zoom_pct` 是阶段一带过来的既有 schema 字段，本阶段首次被 Web 端实际使用（此前只在 `GeneralTab.tsx` 表单里可编辑，未被任何组件读取生效），未改动其定义。
- 新增前端依赖 `@xyflow/react@^12.11.2`：`peerDependencies` 要求 `react`/`react-dom >=17`，与项目 React 19 无冲突；未发现与现有依赖（`recharts`/`lightweight-charts`/`marked`）的版本冲突。`npm install` 过程中出现的 `npm audit` 漏洞警告（3 moderate/1 high/1 critical）经核查均来自 `esbuild`（`vite` 的开发依赖传递引入），非 `@xyflow/react` 本身引入，且仅影响本地开发服务器，不影响生产构建产物，与阶段一/二/三安装依赖时的既有基线一致（未在本阶段专门验证该基线是否随 `npm install` 版本浮动变化，如需消除警告需要单独评估 `vite` 大版本升级，超出本阶段范围）。

## 8. 遗留问题和风险

- **自动播放的相机运镜是"节点到节点跳跃缓动"而非桌面端的连续匀速插值**：见 §3 第 3 条。功能行为对齐（自动开始、显示进度百分比、点击中断、播放完成后 `fitView`），但视觉观感与桌面端的"沿路径飞行"有差异。如果您认为这个差异不可接受，需要额外实施 `requestAnimationFrame` 驱动的连续插值（工作量：新增一个基于时间的相机 tween 循环，替换现有 `setTimeout` 链）。
- **未在真实 DeepSeek API 输出上验证过流程图对 `program_answer`/`program_branch`/`override_reason` 等边缘字段的实际渲染效果**：与阶段三总结报告 §8 遗留问题相同的性质——本阶段 pytest/e2e 均使用手工构造的 trace 数据，覆盖了"AI覆盖"徽章分支，但未跑过真实模型输出。桌面端同样依赖这些字段，理论上行为一致，建议您在有真实 API Key 的环境下跑一次真实分析并人工核对流程图渲染。
- **未做"重新播放"以外的手动重新布局/拖拽/导出图片交互**（严格遵守执行方案 §2 非目标），如果后续发现用户需要手动微调节点位置或导出静态图片，需要作为独立议题提出，不在阶段四范围内补充。
- **移动端/窄屏幕下 `.flow-row` 固定 480px 高度未做响应式适配**：当前布局假设桌面浏览器宽屏使用（与整个 Web 端项目的既有假设一致，`main-layout` 也是固定 grid 布局，未见响应式设计），未在本阶段引入断点适配，与项目现状一致，不算新增风险。

## 9. 是否允许进入下一阶段

**允许**。§7 全部验证已实际运行且通过（后端 60 passed、前端 tsc/vitest/build 均通过、Playwright e2e 3 场景通过）；阶段一/阶段二/阶段三回归全部通过；`pa_agent/gui/`、阶段二报告页面、阶段三决策树表格/树面板代码零改动；`phase-5-execution-plan.md` 已生成。
