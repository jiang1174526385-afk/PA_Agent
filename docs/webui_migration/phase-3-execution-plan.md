# 阶段三执行方案：决策树回放面板（DecisionTreePanel）

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-2-completion-report.md`](phase-2-completion-report.md)（状态 `complete`，含 §0.4 待您确认的默认决策，与阶段三无依赖关系）
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段四内容（动画流程图可视化）及之后各阶段。

## 1. 阶段目标

把 `pa_agent/gui/decision_tree_panel.py`（`QTreeWidget` 完整决策树 + `QTableWidget` 路径回放）迁移为 Web 组件，读取阶段一 `/ws/analysis` 已产出的同一份 `AnalysisRecord` 数据，视觉沿用**阶段一暗色主题**（`tokens.css`，与阶段二的浅色仪表盘主题完全无关——见总纲 §2.1）。

## 2. 非目标

- 不实现动画流程图（阶段四）、自由对话/调试面板（阶段五）、演示模式/下单机会通知（阶段六）。
- 不改动阶段二的报告页面/浅色主题任何代码。
- 不改动 `pa_agent/ai/decision_tree.py`（`merge_traces`/`format_trace_answer`/`normalize_bar_range`/`load_decision_tree` 等）的既有逻辑本身——Web 端只调用/复用，不复制一份改写。
- 不改动 `TwoStageOrchestrator`/`AnalysisRunner` 的决策链路。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-2-completion-report.md`。
2. `git status --short`，确认阶段二的改动已按用户要求处理（提交或保留在工作区），不得回滚。
3. 通读 `pa_agent/gui/decision_tree_panel.py`（已在阶段二 session 读过一次，见下方 §4 摘要，但实施 session 开始时仍需重新打开核对，不能只读本文字复述——尤其是 `_fill_path_table`/`_build_static_tree` 的具体渲染细节）。
4. 通读 `pa_agent/ai/decision_tree.py` 全文（`merge_traces`/`format_trace_answer`/`normalize_bar_range`/`plain_trace_question`/`strip_question_bar_basis_suffix`/`format_bar_basis_suffix`/`load_decision_tree`），确认这些函数当前只在 GUI 侧被调用，还是有可被 Web 后端直接 import 复用的纯函数（大概率可以直接复用，因为它们不依赖 PyQt）。
5. 确认 `AnalysisRecord.stage1_diagnosis`/`stage2_decision` 序列化后是否已包含 `gate_trace`/`decision_trace`/`terminal` 字段——阶段二 session 中已确认这些字段目前存在于 `stage1_json`/`stage2_full` 的原始 dict 里（`pa_agent/ai/decision_tree.py:391` 读 `stage1_json.get("gate_trace")`；`trade_logger.py` 读 `stage2_full.get("terminal")`/`stage2_full.get("decision_trace")`），但**未验证** `/ws/analysis` 的 WS 消息（`pa_agent/webui/services/analysis_runner.py`）和阶段一 `records/schema.py::AnalysisRecord` 转发给前端时是否原样保留了这两个 key，还是被裁剪掉了。这是本阶段第一个需要实际验证（不能假设）的事实。

## 4. 当前代码事实摘要（实施时仍需按需核实）

- `DecisionTreePanel.set_trace(gate_trace, decision_trace, terminal, gate_result, gate_shortcircuited)` 是唯一的数据绑定入口，包含三部分 UI：
  1. 终点横幅（`_terminal_banner`）：显示 `outcome`(wait/reject/trade/proceed) + `label`，颜色随 outcome 变化。
  2. 路径回放表格（`_path_table`，6 列：步/阶段/节点/回答/K线依据/理由）：数据来自 `merge_traces(gate_trace, decision_trace)`，每行可悬停查看完整问题/依据/理由的 tooltip，点击行会滚动高亮下方完整树中的对应节点。
  3. 完整决策树（`_tree`，`QTreeWidget`）：来自 `load_decision_tree()`（静态决策树定义，不依赖具体某次分析），按 `_visited_ids`（本次分析实际走过的节点）高亮显示，未走过的节点显示为灰色。
- `gate_shortcircuited=True` 时（阶段一闸门 wait/unknown，未调用阶段二模型），额外提示"决策页显示的不下单是程序生成的占位，非模型评估"。
- Web 端已有 `/ws/analysis` 推送 `record`(`AnalysisRecord`) 消息（`pa_agent/webui/frontend/src/types/domain.ts::AnalysisWsInbound`），前端 `AnalysisRecord` 类型目前只显式声明了 `stage1_diagnosis: Record<string, unknown> | null` / `stage2_decision: StageDecision | null`（`StageDecision` 未包含 `decision_trace`/`terminal`/`gate_trace` 字段），意味着这些字段即使后端已经在传，前端类型层面也还没有解析出来——阶段三需要在 `types/domain.ts` 补上这些字段的类型（保持"前后端手工同步"的既有约定，见总纲 §7）。

## 5. 实施步骤（草案，实施 session 应据实调整）

1. **验证数据链路**（对应 §3.5 的事实核实）：在真实一次 `/ws/analysis` 分析（可复用阶段一 `AnalysisRunner`，用真实或 e2e fake orchestrator 均可）中打印/断言 WS 推送的 `record.stage1_diagnosis.gate_trace`、`record.stage2_decision.decision_trace`、`record.stage2_decision.terminal` 是否存在。如果缺失，需要在 `pa_agent/webui/services/analysis_runner.py` 或 `AnalysisRecord` 序列化路径补上（最小必要改动，需在总结报告说明），而不是自行在前端伪造。
2. **后端**：评估是否需要新增 API，还是纯前端消费已有 `/ws/analysis` record 数据即可——大概率不需要新增 REST 端点（决策树数据已经随分析结果一起推送），如果发现需要独立于 WS 之外单独查询某条历史记录的决策轨迹（例如刷新页面后需要重新拉取上一条分析的树），才需要评估是否新增 `GET /api/analysis/last-record` 之类的端点。
3. **`load_decision_tree()`/`merge_traces()`等纯函数是否可直接被 Web 后端 import 复用，还是需要一个薄的 JSON 序列化包装**（这些函数在 `pa_agent/ai/decision_tree.py`，不依赖 PyQt，理论上可以直接 import 到 FastAPI 层用于把结果打包成 JSON 返回给前端，而不是让前端重新实现一遍"合并 trace/格式化答案"的逻辑）。
4. **前端组件**：`src/decisionTree/`（沿用阶段一暗色主题，import 现有 `tokens.css`，不新建独立主题）：
   - `DecisionTreePanel.tsx`：终点横幅 + 路径回放表格 + 完整树（可用简单的可展开/折叠 `<ul>`/`<li>` 结构模拟 `QTreeWidget` 的两级结构，不需要引入新的树形组件库，除非现有 HTML 结构不足以表达折叠交互）。
   - 路径表格行点击 → 树节点高亮/滚动的联动逻辑对应桌面端 `_on_path_row_selected`/`_scroll_tree_to_node`。
5. **类型同步**：`src/types/domain.ts` 补充 `gate_trace`/`decision_trace`/`terminal` 相关类型（结构对齐后端实际 JSON，不臆造字段）。

## 6. 兼容策略与回滚点

- 新增代码位于 `pa_agent/webui/frontend/src/decisionTree/`；如需后端改动，限定在 `pa_agent/webui/services/analysis_runner.py`（若确有必要透传缺失字段）和一个可能的新 `pa_agent/webui/api/*.py` 文件。回滚只需删除这些路径 + 还原 `analysis_runner.py` 的最小 diff。
- `pa_agent/ai/decision_tree.py`/`pa_agent/gui/decision_tree_panel.py` 均不改动，桌面 GUI 决策树面板行为不受影响。

## 7. 测试与验证命令

- 后端 pytest：若 §5.1 发现需要透传字段，需补充断言 WS `record` 消息包含 `gate_trace`/`decision_trace`/`terminal` 的测试。
- 前端：`tsc --noEmit`/`npm run build`/`npx vitest run`（trace 合并/格式化的展示函数，如果前端有自己的一层格式化）。
- Playwright e2e：`tests/webui/e2e/test_phase3_decision_tree_smoke.py`——提交一次分析后，断言终点横幅显示正确的 outcome 文案、路径回放表格行数与 `merge_traces` 结果一致、点击某行后对应树节点高亮/滚动到可见区域。

## 8. 验收标准

- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 阶段一暗色主题/工作台功能回归验证仍全部通过（`tests/webui/`、`e2e/test_phase1_smoke.py`）。
- 阶段二报告页面回归验证仍全部通过（`tests/webui/test_reports_api.py`、`e2e/test_phase2_reports_smoke.py`）——决策树面板改动理论上与阶段二完全无交集，但既然三个阶段共享同一个前端项目/后端进程，仍需跑一遍确认没有意外的构建/路由冲突。
- 已生成 `phase-3-completion-report.md` 和 `phase-4-execution-plan.md`。

## 9. 停止条件

- 如果 §3.5 验证发现 `AnalysisRecord`/`AnalysisRunner` 当前**没有**透传 `gate_trace`/`decision_trace`/`terminal`，且需要改动的范围超出"补一两个字段透传"（例如发现这些字段在 `stage1_json`/`stage2_full` 里本身就不完整或结构对不上 `pa_agent/ai/decision_tree.py` 的预期），必须暂停向用户确认，不得自行改动 Stage1/Stage2 的 JSON 输出结构来"凑"出决策树需要的字段。
- 如果发现完整决策树的静态定义（`load_decision_tree()` 读取的数据文件）本身有 GUI 特有的展示假设（例如依赖 PyQt 的富文本/图标资源）导致无法直接序列化为 JSON，需要停下向用户确认改造范围。
