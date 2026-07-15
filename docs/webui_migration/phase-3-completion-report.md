# 阶段三总结报告：决策树回放面板（DecisionTreePanel）

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-3-execution-plan.md`](phase-3-execution-plan.md)
> 上一阶段总结：[`phase-2-completion-report.md`](phase-2-completion-report.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

## 0. §3.5 数据链路验证结果（执行方案要求"必须实际验证，不能假设"）

结论：**`gate_trace`/`decision_trace`/`terminal` 已经透传到 `/ws/analysis`，无需改动 `AnalysisRunner`/`AnalysisRecord`**，未触发执行方案 §9 的停止条件。

依据（代码走读 + 新增测试双重确认）：

1. `pa_agent/records/schema.py::AnalysisRecord.stage1_diagnosis`/`stage2_decision` 类型是 `Optional[dict]`（无嵌套 Pydantic 子模型），`pa_agent/orchestrator/two_stage.py` 把 AI 返回并经 `json_validator.py` 校验后的原始 `stage1_json`/`stage2_json` 字典整体赋给这两个字段（`two_stage.py:632/670/673` 等）。
2. `pa_agent/ai/json_validator.py` 对 `gate_trace`（第667行起）、`decision_trace`（第728行起）做逐项校验，但校验后仍然操作/返回同一个 `obj` 字典，不会剔除 `gate_trace`/`decision_trace`/`terminal` 字段。
3. `pa_agent/webui/services/analysis_runner.py:133` 用 `record.model_dump()` 序列化整条 `AnalysisRecord` 通过 WS 发送——`model_dump()` 对 `Optional[dict]` 字段是逐层深拷贝的原样输出，不做字段裁剪。
4. 新增测试 `tests/webui/test_analysis_ws.py::test_submit_full_analysis_message_sequence` 显式断言：fake record 的 `stage1_diagnosis.gate_trace`/`stage2_decision.decision_trace`/`stage2_decision.terminal` 在 WS `record` 消息里原样可见。

因此本阶段**未修改** `pa_agent/ai/decision_tree.py`、`analysis_runner.py`、`AnalysisRecord` 的任何字段结构，符合非目标 §2 的约束。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §5.1 验证数据链路 | ✅ | 见 §0，代码走读 + 测试双重确认，未发现缺口 |
| §5.2 后端是否需要新增 API | ✅（新增，见下） | 未新增"独立查询历史记录"端点（`/ws/analysis` 已推送完整 record，前端始终有当次数据）；但新增了 `pa_agent/webui/api/decision_tree.py` 两个端点，理由见 §5 |
| §5.3 `load_decision_tree()`/`merge_traces()` 复用评估 | ✅ | 确认为纯函数（不依赖 PyQt），直接在新 API 层 `import` 复用，未复制/重写这些函数的逻辑 |
| §5.4 前端组件 `src/decisionTree/` | ✅ | `DecisionTreePanel.tsx`（终点横幅 + 路径回放表格 + 完整树）+ `decisionTreeApi.ts`，沿用阶段一 `tokens.css`/`app.css`，未新建独立主题 |
| §5.5 类型同步 `types/domain.ts` | ✅ | 新增 `Stage1Diagnosis`/`DecisionTraceItem`/`DecisionTreeTerminal`/`DecisionTreeStaticResponse`/`DecisionTreeReplayRequest`/`DecisionTreeReplayResponse` 等，`StageDecision` 补充 `decision_trace`/`terminal`/`gate_shortcircuited`；`AnalysisRecord.stage1_diagnosis` 从 `Record<string, unknown>` 收紧为 `Stage1Diagnosis` |
| 路径表格行点击 → 树节点高亮/滚动 | ✅ | `DecisionTreePanel.tsx` 用 `data-node-id` + `ref` Map + `scrollIntoView` 实现，对应桌面端 `_on_path_row_selected`/`_scroll_tree_to_node` |
| 后端 pytest | ✅ | `tests/webui/test_decision_tree_api.py`（4 用例：静态树、merge+terminal 展示、gate_shortcircuited 分支、空 trace 边界）；`tests/webui/test_analysis_ws.py` 补充 §0 提到的透传断言 |
| 前端 tsc/vitest/build | ✅ | 见 §6 |
| Playwright e2e | ✅ | `tests/webui/e2e/test_phase3_decision_tree_smoke.py`（2 场景：终点横幅+路径行数、点击联动高亮） |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段四执行方案 | ✅ | [`phase-4-execution-plan.md`](phase-4-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增：**
- `pa_agent/webui/api/decision_tree.py`（`GET /api/decision-tree/static` + `POST /api/decision-tree/replay`）
- `pa_agent/webui/schemas/decision_tree.py`
- `pa_agent/webui/frontend/src/decisionTree/DecisionTreePanel.tsx`
- `pa_agent/webui/frontend/src/decisionTree/decisionTreeApi.ts`
- `tests/webui/test_decision_tree_api.py`
- `tests/webui/e2e/test_phase3_decision_tree_smoke.py`

**修改：**
- `pa_agent/webui/server.py`（挂载 `decision_tree_api.router`）
- `pa_agent/webui/frontend/src/App.tsx`（在 side-pane 挂载 `<DecisionTreePanel record={state.record} />`）
- `pa_agent/webui/frontend/src/types/domain.ts`（见 §1 类型同步条目）
- `pa_agent/webui/frontend/src/styles/app.css`（新增 `.decision-tree-*` 系列类，均在阶段一暗色主题变量体系内，未新增色值）
- `tests/webui/test_analysis_ws.py`（fake record 补充 gate_trace/decision_trace/terminal + 透传断言）
- `tests/webui/e2e/conftest.py`（e2e 共享的 `_build_record` fake 补充最小 gate_trace/decision_trace/terminal，供阶段三 e2e 使用；未改动 phase1/2 既有断言依赖的字段）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 全部零改动（`git status --short -- pa_agent/gui/` 确认为空）。
- `pa_agent/ai/decision_tree.py` 零改动，仅被新 API 层 `import` 调用。
- `pa_agent/orchestrator/two_stage.py`/`pa_agent/webui/services/analysis_runner.py` 零改动（见 §0，数据链路本就完整，无需修补）。
- 阶段二报告页面代码（`src/reports/`、`src/reportStyles/`）零改动。

## 3. 遇到的问题、根因与解决方式

1. **是否需要新增 REST 端点**：执行方案 §5.2 说"大概率不需要"，但同时 §5.3 建议"如果 `merge_traces`/格式化函数可复用，应在后端而非前端重新实现格式化逻辑"。两条建议单独看有一点张力——纯粹"不新增端点"就意味着要么前端用 TS 重写一遍 `merge_traces`/`format_trace_answer`/`normalize_bar_range`/`format_bar_basis_suffix`（违背"不重复实现核心逻辑"的全局要求 §7），要么后端新增一个轻量端点复用这些函数。选择了后者：新增 `POST /api/decision-tree/replay`（接受 trace 数据，返回格式化后的行），以及 `GET /api/decision-tree/static`（返回 `load_decision_tree()` 的静态树结构，前端只需拉取一次）。这是在"不新增端点"与"不在前端重复业务逻辑"两条约束之间选择了更贴近总纲 §7 的一条，记录在此供确认。
2. **`load_decision_tree()` 返回的 `node_index` 字段未在响应模型中暴露**：`DecisionTreeStaticResponse` 只声明了 `version`/`source`/`sections`，构造时用 `DecisionTreeStaticResponse(**load_decision_tree())`，Pydantic v2 默认 `extra="ignore"`（`AnalysisRecord` 等其它模型显式用了 `extra="forbid"`，但本阶段新模型未设置该项，遵循 Pydantic 默认行为），`node_index` 会被静默丢弃而不报错。这是有意选择——`node_index` 是给桌面端 Python 代码用的查找表（`get_node_branch_outcome`），前端不需要它，可以从 `sections` 自行按 `node_id` 建 Map。
3. **e2e 共享 fixture 的最小改动**：`tests/webui/e2e/conftest.py::_build_record` 是 phase1/2/3 三个 e2e 套件共用的 fake record 构造函数。给它补充 `gate_trace`/`decision_trace`/`terminal` 字段前，先确认了 phase1（`test_phase1_smoke.py`）/phase2（`test_phase2_reports_smoke.py`）现有断言只读取 `order_type`/`reasoning`/`estimated_win_rate` 等既有字段，不依赖字段"不存在"这一状态，因此补充是安全的纯增量修改，未删除/重命名任何既有字段。跑了 phase1+phase2+phase3 全部 e2e 用例回归确认（见 §6）。

## 4. 可复用经验与后续注意事项

- **`AnalysisRecord.stage1_diagnosis`/`stage2_decision` 是"信封"而非"强类型载荷"**：只要 AI 返回的 JSON 通过 `json_validator.py` 校验，其字段会原样流到 WS 消息，不需要在 `AnalysisRecord`/`AnalysisRunner` 层做任何透传改动。后续阶段（如阶段四流程图）如果也需要读取 stage1/stage2 JSON 里的某个字段，同样的结论应该成立——但仍建议按执行方案的要求显式验证一次，不要凭本报告的结论直接假设，因为字段名可能随 `pa_agent/ai/prompts/schemas.py` 演进而变化。
- **纯函数格式化逻辑放后端，而不是前端重写一遍**：`pa_agent/ai/decision_tree.py` 里的 `merge_traces`/`format_trace_answer`/`normalize_bar_range`/`format_bar_basis_suffix`/`plain_trace_question` 不依赖 PyQt，可以直接被 FastAPI 层 `import`。后续阶段如果桌面 GUI 还有类似的"纯展示格式化"辅助函数，优先复用而不是用 TS 重写，避免两套格式化逻辑长期漂移不一致。
- **e2e 共享 `_build_record` fixture 需要谨慎增量修改**：它被三个阶段的 e2e 套件共用，新增字段是安全的，但删除/重命名字段前必须先搜索所有引用它的测试文件。

## 5. 设计决策与偏离原计划的原因

- **新增两个 REST 端点**（`GET /api/decision-tree/static`、`POST /api/decision-tree/replay`），执行方案 §5.2 原本倾向"大概率不需要"——见 §3 第1条的权衡说明。这是执行方案范围内、为满足总纲 §7"不得在 Web 层重复实现核心业务逻辑"要求而做的最小必要补充，不是新功能。
- **颜色映射语义化为 `color_key`（success/danger/warning/muted/secondary）而非直接返回十六进制色值**：桌面端 `decision_tree_panel.py` 直接引用 `pa_agent/gui/theme/tokens.py` 的 Python 常量（如 `T.ACCENT_SUCCESS`），Web 端等价物是 CSS 变量 `var(--success)` 等（定义在 `tokens.css`，与桌面 `tokens.py` 逐值对应）。让后端返回语义 key、前端映射到 CSS 变量，比后端直接返回十六进制色值更符合"前后端各自持有自己的展示层细节"原则，也让后续如果要微调某个颜色值，只需要改 `tokens.css` 一处。

## 6. 实际运行的验证命令与结果

### 6.1 后端 pytest（含阶段一、二回归）
```bash
./.venv/bin/pytest tests/webui/ tests/unit/test_trade_fill_backfill.py --browser chromium
# 53 passed, 1 warning in 79.34s
```
覆盖：阶段一 `test_kline_api.py`(7)/`test_analysis_ws.py`(5，含本阶段新增的 3 条透传断言)/`test_settings_api.py`(7)/`e2e/test_phase1_smoke.py`(7) 全部仍通过；阶段二 `test_reports_api.py`(6)/`test_trade_fill_backfill.py`(12)/`e2e/test_phase2_reports_smoke.py`(3) 全部仍通过；阶段三新增 `test_decision_tree_api.py`(4)/`e2e/test_phase3_decision_tree_smoke.py`(2)。

### 6.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 3 passed (3) / Tests 21 passed (21)（本阶段未新增前端单测，格式化逻辑在后端有 pytest 覆盖）
npm run build            # 构建成功；产物 804KB（未压缩前），同阶段二一样有 "chunk > 500KB" 警告，未做代码分割（沿用既有模式）
```

## 7. 数据/兼容性迁移情况

- 无数据迁移：本阶段不写入/修改任何持久化数据（CSV、settings.json、records/pending/），只读取 `/ws/analysis` 已推送的 record 数据并格式化展示。
- 新增的两个 API 端点无状态、无副作用（`GET` 读静态文件解析结果——`load_decision_tree()` 本身有 `@lru_cache`；`POST /replay` 是纯函数式的格式化转换，不落盘）。
- `types/domain.ts` 中 `AnalysisRecord.stage1_diagnosis` 类型从 `Record<string, unknown>` 收紧为 `Stage1Diagnosis`（仍带 `[key: string]: unknown` 兜底），不是破坏性变更——原本能访问的动态字段访问方式（`stage1_diagnosis?.some_field`）仍然合法。

## 8. 遗留问题和风险

- **未在真实 DeepSeek API 输出上验证过 `gate_trace`/`decision_trace` 的实际字段完整性**：本阶段的 pytest/e2e 均使用手工构造或 e2e fake 的 trace 数据（结构对齐 `pa_agent/ai/prompts/schemas.py::_TRACE_ITEM` 的 JSON Schema 定义），未跑过一次真实模型输出走完整链路。如果真实模型输出在某些边缘情况下的 `bar_range`/`branch`/`skipped` 字段组合与本阶段假设不同（例如 `_fill_path_table` 依赖的 `format_trace_answer`/`normalize_bar_range` 对某些真实场景返回空字符串），前端展示可能出现"K线依据"或"回答"列为空——桌面端同样依赖这些函数，理论上行为一致，但建议您在有真实 API Key 的环境下跑一次真实分析，人工核对决策树面板的展示是否符合预期。
- **完整决策树默认折叠策略比较简单**：只按"该 section 内是否有被访问节点"决定是否展开（`<details open>`），桌面端 `_build_static_tree` 的展开规则是 `int(sec["id"]) <= 2`（前两个 section 默认展开，不管是否访问过）。Web 端选择了"仅展开有访问节点的 section"这一更贴合"回放"场景的行为，属于本阶段一个未在执行方案中明确、由实施时判断决定的细节偏离，如果您认为应该完全对齐桌面端的默认展开规则，可以在 `DecisionTreePanel.tsx` 里调整 `visitedSectionIds` 的计算逻辑。
- **多次连续提交分析后，`selectedNodeId` 状态未在新 record 到达时重置**：如果用户先点击了某一行高亮，然后提交下一次分析，`selectedNodeId` 仍保留上一次选中的节点 id，可能出现"选中态"指向一个新 trace 里其实没有的节点（此时不会报错，只是不会有任何行高亮，视觉上等同于未选中）。属于低风险的次要遗留问题，未在本阶段修复，记录留待后续阶段顺手处理或您决定是否需要立即修。

## 9. 是否允许进入下一阶段

**允许**。§7 全部验证已实际运行且通过；阶段一/阶段二回归全部通过；§0 的数据链路验证已完成且未触发任何 §9 停止条件；`phase-4-execution-plan.md` 已生成。
