# 阶段四执行方案：动画流程图可视化（DecisionFlowViz）

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-3-completion-report.md`](phase-3-completion-report.md)（状态 `complete`）
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段五内容（自由对话 + AI 调试面板）及之后各阶段。

## 0. 需要您决策的问题（实施 session 开始前应先确认，不得自行假设）

1. **渲染方案：`react-flow`（新增前端依赖）还是手写 SVG/Canvas？** 总纲 §5 阶段四条目把这个作为候选二选一，未定论。`react-flow` 能省去节点定位/连线/缩放/拖拽的底层实现，但会引入一个新的前端依赖（需要评估包体积——阶段二已经因为 `recharts` 产生过一次"新增依赖"的确认动作，见 `phase-2-completion-report.md` §7.3）；手写 SVG/Canvas 更可控、无新依赖，但需要自己实现节点布局算法和动画时序，工作量显著更高（桌面端 `decision_flow_viz.py` 本身 1215 行，大量代码是 `QPainter` 手绘 HUD 风格特效——见 §4）。**建议先用 `react-flow` 做静态节点/连线骨架，动画特效（发光、粒子、扫描线等）视觉复杂度足够时再评估是否需要 Canvas 叠加层**，但这只是建议，不是本报告可以替您做的决定。
2. **动画保真度目标**：桌面端有大量霓虹/HUD 风格特效（角标装饰 `_draw_corner_brackets`、发光描边、`_PLAY_TICK_MS`/`_FX_TICK_MS` 双时钟驱动的呼吸动画等，见 §4）。Web 端是否需要 1:1 还原这些视觉特效，还是只需要"节点高亮 + 连线流动"这一级别的简化动画？这直接决定工作量和技术选型（简化版用 CSS animation/transition 即可，高保真版可能需要 Canvas 逐帧绘制）。
3. **自动播放（`decision_flow_auto_play`/`decision_flow_play_seconds`）是否本阶段一起实现**：`GeneralRead`（`pa_agent/webui/schemas/settings.py`）已经有这两个设置字段（阶段一带过来的既有 schema），桌面端流程图有自动播放模式。本阶段只做静态展示 + 手动交互，还是把自动播放也纳入范围？

## 1. 阶段目标

把 `pa_agent/gui/decision_flow_viz.py`（`QGraphicsView`/`QGraphicsScene` 动画流程图，二叉决策树的可视化版本，与阶段三的表格/树形回放是同一份 `gate_trace`/`decision_trace`/`terminal` 数据的另一种展示形式）迁移为 Web 组件。视觉沿用**阶段一暗色主题**。这是全项目单项工作量最大的部分。

## 2. 非目标

- 不实现自由对话/调试面板（阶段五）、演示模式/下单机会通知（阶段六）。
- 不改动阶段二报告页面、阶段三决策树表格/树面板的任何代码。
- 不改动 `pa_agent/ai/decision_tree.py`、`AnalysisRecord`/`AnalysisRunner` 的既有逻辑——阶段三已确认 `gate_trace`/`decision_trace`/`terminal` 已完整透传到 `/ws/analysis`（见 `phase-3-completion-report.md` §0），阶段四直接复用同一份数据，理论上不需要新的后端字段。
- 不在本阶段引入自动播放之外的额外交互（如手动拖拽重新布局节点、导出图片等），除非 §0.3 的决策要求。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-3-completion-report.md`。
2. `git status --short`，确认阶段三的改动已按用户要求处理，不得回滚。
3. **完整通读 `pa_agent/gui/decision_flow_viz.py`（1215 行）**——本执行方案只读了前 120 行左右用于给出大致方向，远未覆盖动画时序（`_PLAY_TICK_MS`/`_FX_TICK_MS` 双定时器）、节点分支布局算法（`_taken_branch_side`/`_LEVEL_DY`/`_BRANCH_DX` 等常量背后的坐标计算逻辑，本文件未展开读取）、`QGraphicsObject` 子类的绘制细节。这些必须在实施 session 完整读完后才能定稿具体步骤，本执行方案的 §5 只是骨架。
4. 确认 §0 三个决策问题已经和您对齐。
5. 复用阶段三已确认的结论：`gate_trace`/`decision_trace`/`terminal` 数据链路完整，无需再次验证（除非阶段四发现桌面端流程图用到了阶段三未涉及的额外字段，例如 `program_answer`/`overridden_by_ai`/`next_node` 等 `_TRACE_ITEM` schema 里存在但阶段三格式化逻辑未使用的字段——需要在实施时核对 `decision_flow_viz.py` 是否读取了这些字段，如果读取了但阶段三 API 没有透传，需要评估是否扩展 `pa_agent/webui/api/decision_tree.py` 的响应，而不是重新发明一套格式化逻辑）。

## 4. 当前代码事实摘要（不完整，实施时必须重新通读全文核实）

- 依赖 `pa_agent/ai/decision_tree.py` 的 `merge_traces`/`format_trace_answer`/`plain_trace_question`/`get_node_branch_outcome`，以及一个阶段三未使用到的私有符号 `_BRANCH_DISPLAY_ZH`（下划线前缀，理论上是模块内部实现细节，桌面端 `decision_flow_viz.py` 却直接 import 了它——实施时需确认这是否应该提升为公开 API，或者 Web 端改用 `format_trace_answer` 已经处理过分支展示的返回值，避免复制一份私有映射表）。
- 节点卡片尺寸/布局用像素常量硬编码（`_NODE_W=580`/`_NODE_H=196`/`_LEVEL_DY=270`/`_BRANCH_DX=360`），这是 `QGraphicsScene` 坐标系的产物，Web 端如果用 `react-flow` 大概率需要换算成该库的布局模型（`react-flow` 有自己的节点定位 API），如果手写 SVG 则可以直接复用这套比例关系。
- 分支方向判定 `_taken_branch_side`：否→左，是/等待/中性→右，跳过→下。这是节点连线走向的核心规则，Web 端无论用什么渲染方案都需要复刻同样的分支布局语义，保证"AI 实际走过的路径"在视觉上可辨识。
- `_OUTCOME_COLOR`/`_ANSWER_COLOR` 复用了阶段三已经在后端做过语义化（`success`/`danger`/`warning`/`muted`）的同一套颜色语义（见 `phase-3-completion-report.md` §5 的 `color_key` 设计）——阶段四如果新增流程图专属的格式化端点，应该延续同一套 `color_key` 命名，不要另起一套。

## 5. 实施步骤（骨架，实施 session 必须先完整读完 `decision_flow_viz.py` 全文再据实调整/展开）

1. 完整通读 `decision_flow_viz.py` 全文，梳理：节点数据模型（有哪些节点类型：普通节点/存根节点/终点节点，对应 `_NODE_W`/`_STUB_W`/`_TERMINAL_W` 三种尺寸）、连线绘制逻辑、动画驱动方式（两个 QTimer 分别驱动什么）、`QShowEvent`/`resizeEvent` 之类的响应式布局处理。
2. 根据 §0.1 的决策，选定渲染技术栈；如选 `react-flow`，评估版本/包体积/是否有 React 18/19 兼容性问题（本项目 React 版本需要在 `package.json` 里确认）。
3. 设计节点/边的 JSON 数据模型——大概率可以复用阶段三 `pa_agent/webui/api/decision_tree.py::replay` 返回的 `rows`（已经是 merge 后的顺序数据），额外补充"分支方向"信息（`_taken_branch_side` 等价的字段）。评估是扩展现有 `/api/decision-tree/replay` 响应，还是新建一个流程图专属端点——原则同阶段三 §3：优先复用已有格式化数据，避免前端重新实现分支判定逻辑。
4. 前端组件：`src/decisionFlow/`（沿用暗色主题）。
5. 动画方案实现（保真度取决于 §0.2 的决策）。
6. 自动播放（如果 §0.3 决定纳入范围）：读取 `GeneralRead.decision_flow_auto_play`/`decision_flow_play_seconds` 设置。

## 6. 兼容策略与回滚点

- 新增代码位于 `pa_agent/webui/frontend/src/decisionFlow/`；如需扩展后端响应，限定在 `pa_agent/webui/api/decision_tree.py`/`pa_agent/webui/schemas/decision_tree.py` 的最小必要增量（新增字段，不删除/不重命名阶段三已有字段，保证阶段三面板不受影响）。
- `pa_agent/gui/decision_flow_viz.py`、`pa_agent/ai/decision_tree.py` 均不改动。

## 7. 测试与验证命令

- 后端 pytest：若扩展了 `/api/decision-tree/replay` 响应或新增端点，需要对应的新增/更新用例。
- 前端：`tsc --noEmit`/`npm run build`/`npx vitest run`。
- Playwright e2e：`tests/webui/e2e/test_phase4_decision_flow_smoke.py`——提交一次分析后，断言流程图渲染出节点、终点节点可见、（如实现动画）动画未导致页面报错或卡死。

## 8. 验收标准

- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 阶段一/二/三回归验证仍全部通过。
- 已生成 `phase-4-completion-report.md` 和 `phase-5-execution-plan.md`。

## 9. 停止条件

- §0 三个决策问题未获得您的确认前，不得开始实施（尤其是新增 `react-flow` 依赖这类需要显式确认的技术选型，参照总纲 §3.3"依赖冲突/技术方案不确定必须暂停询问"）。
- 通读 `decision_flow_viz.py` 全文后，如果发现动画/交互复杂度远超本文件 §4 的摘要判断（例如存在本文件完全未提及的额外交互模式），需要重新评估工作量并向您报告，不得为了赶进度简化到明显偏离桌面端行为的程度而不说明。
