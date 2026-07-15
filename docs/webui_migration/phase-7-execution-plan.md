# 阶段七执行方案：文档收尾与最终清理

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-6-completion-report.md`](phase-6-completion-report.md)（状态 `complete`）
> Session 规则：本执行方案必须在一个独立 Session 中完成；这是七个阶段里的最后一个 session，完成后整个 `docs/webui_migration/` 迁移项目结束。

## 0. 需要您决策的问题（实施 session 开始前应先确认，不得自行假设）

1. **是否借阶段七顺手修复阶段一 `DecisionPanel.tsx` 可能存在的 `stage2_decision` 拆包问题**（见 `phase-6-completion-report.md` §3 第 1 条、§8 第一条）：真实生产的 `stage2_decision` 是 `{"decision": {order_type, ...}, ...}` 嵌套形状，但 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 目前直接读取 `decision.order_type` 等顶层字段，只有在本项目历次 e2e/pytest 使用的"扁平测试夹具"下才能正确显示；如果真实生产数据确实是嵌套的，意味着 Web 端「决策」标签页在真实分析下可能显示不全（`order_type`/`entry_price` 等会读到 `undefined`）。这是阶段一遗留、跨越多个阶段都未被发现的问题，属于"高风险的跨阶段变更"，README §3.2 要求"超出阶段边界的高风险变更必须停止并记录，不能用临时补丁悄悄跨阶段"——因此列入本阶段决策问题而非默认修复。若确认要修，需要评估是否也影响阶段三决策树面板/阶段四流程图（它们读取的 `decision_trace`/`terminal` 字段本身就是真实数据的顶层字段，大概率不受影响，但需要重新核实）。
2. **`pa_agent/records/trade_logger.py::save_trade_record()` 是否需要接入 Web 端下单机会触发流程**（阶段六执行方案未列入交付项，`phase-6-completion-report.md` §5/§8 已记录）：桌面端下单机会触发时除了发通知还会写入 `trade_records/*.csv`（阶段二报告页面的数据源）；Web 端目前只发通知，不写 CSV。如果需要补齐，需要确认 `chart_image_path`（桌面端截图后传给飞书）在无桌面截图能力的 Web 端如何处理（继续传 `None`，还是需要新增图表截图功能——后者工作量较大，可能需要独立评估）。
3. **`config/settings.json` 中 `notify_on_order_only`(飞书) 字段是否需要在本阶段补上读取生效逻辑**：该字段自阶段一存在起从未被任何一端（桌面/Web）读取生效，阶段六执行方案明确决定"不引入"。如果确认这就是废弃字段，本阶段的"清理迁移期间产生的临时兼容代码"是否应该顺带把它从 DTO/前端表单里移除（属于对既有 UI 的删除性改动，需要您确认是否属于阶段七"最终清理"范畴，还是保留原样只在文档里说明现状）。
4. **README §5 阶段七条目里的"最终验收报告"范围**：是否需要真实 API Key/真实飞书 webhook/真实 MT5 或 OKX 账户跑一次完整人工验收（阶段一至六总结报告 §8 累计了多条"未在真实环境验证"的遗留项，见 §4），还是仅需在报告里列出这些遗留项、验收报告本身仍基于自动化测试 + 开发者本地一次手动 smoke（不接真实凭证）。

## 1. 阶段目标

把 Web 版固化为主入口，`pa_agent/gui/` 标注为 legacy/参考实现，清理迁移期间产生的临时兼容代码，做一次全流程演练验收，作为整个 `docs/webui_migration/` 项目的收尾。

## 2. 非目标

- 不新增任何功能性交付（K线/分析/决策树/流程图/自由对话/演示模式/通知触发等功能本身已在阶段一至六完成）。
- 不重构 `pa_agent/gui/` 内部实现，只在文件顶部/README 层面加 legacy 说明。
- 除非 §0 决策要求，否则不修改阶段一至六任何既有面板/接口的行为。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-6-completion-report.md`。
2. `git status --short`，确认阶段六的改动已按用户要求处理，不得回滚。
3. 确认 §0 四个决策问题已经和您对齐（尤其是 §0.1——是否修复 `DecisionPanel.tsx`，这会直接决定本阶段的实施步骤数量和风险等级）。
4. 通读以下累计遗留问题清单（§4），逐条确认是文档记录即可还是需要动代码。

## 4. 当前代码事实摘要：跨阶段累计遗留问题清单（不完整，实施时应重新读取各阶段总结报告 §8 核实）

| 来源阶段 | 问题 | 建议处理方式（本阶段实施时按 §0 决策落实） |
|---|---|---|
| 阶段一 | `AnalysisRunner`/`RefreshBroadcaster` 未做多标签页共享连接（单用户本地场景影响很小） | 文档记录为已知限制，不修 |
| 阶段一 | `GET /api/ai/models` 是硬编码精选列表，非真实模型枚举 | 文档记录为已知限制，不修 |
| 阶段二 | 策略筛选下拉硬编码 `decision_stance` 枚举；OKX/MT5 私有接口字段未经真实账户验证 | 文档记录 |
| 阶段三 | 连续提交分析后 `selectedNodeId` 未随新 record 重置（低风险视觉问题） | 视 §0 决策，若顺手修屬于小范围修复（非"高风险跨阶段变更"） |
| 阶段四 | 自动播放相机运镜为"节点到节点跳跃"简化版，非连续插值 | 文档记录为设计决策，不修 |
| 阶段四/五 | 流程图边缘字段、`/ws/chat` 完整流式行为均未在真实 DeepSeek API 上验证 | 若 §0.4 确认需要真实环境验收，本阶段人工验证一次并记录结果 |
| 阶段六 | `stage2_decision` 嵌套/扁平形状不一致（阶段一 `DecisionPanel.tsx` 可能受影响） | 见 §0.1 |
| 阶段六 | `notify_on_order_only` 未生效；`save_trade_record()` 未接入 Web 端 | 见 §0.2/§0.3 |
| 阶段六 | 飞书/PushPlus 真实推送、随机演示的选择策略较桌面端简化 | 文档记录 |

## 5. 实施步骤（骨架，实施 session 应先完整确认 §0 决策再据实调整/展开）

1. 按 §0 决策，逐条处理 §4 清单里"需要动代码"的项（若 §0.1/§0.2/§0.3 都选择"仅文档记录"，本阶段代码改动应非常小甚至为零）。
2. 更新根 `README.md`/`CONTRIBUTING.md`：说明 Web 端（`pa_agent/webui/`）现为主要交互入口，启动方式（`uvicorn pa_agent.webui.server:app` 或既有的 `pa-agent-web` 等入口，需要先确认实际启动命令是否已存在或需要新增）。
3. `pa_agent/gui/` 顶部（`main_window.py` 及包 `__init__.py`）加 legacy/参考实现说明注释，不改动内部逻辑。
4. 汇总迁移期间产生的临时兼容代码清单（例如阶段五 `.app-shell` 从 `100vh` 改为 `min-height: 100vh` 是否仍视为"临时"还是已经是终态设计，需要重新判断并在文档里定性,而非默认当作待清理项）。
5. 生成最终验收报告：汇总阶段一至七全部自动化验证结果 + （按 §0.4 决策）人工验证记录，覆盖 README §8 列出的关键流程全链路（切数据源 → 拉K线 → 提交分析 → 增量分析 → 取消 → 交易记录报告页面加载与筛选 → 决策树回放 → 流程图动画 → 自由对话 → 演示模式 → 下单机会通知）。

## 6. 兼容策略与回滚点

- 若 §0.1 决定修复 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 的拆包逻辑，改动应限定在这两个组件内部读取 `decision` 字段的方式（例如在读取处统一做一次 `decision.decision ?? decision` 兼容两种形状，而非要求后端改变 `/ws/analysis` 已有的 "record" 消息序列化方式），避免牵动 `/ws/analysis` schema。
- 除 §0 决策要求外，`pa_agent/gui/` 不做内部逻辑改动，必须保持可独立运行。
- 全部改动完成后仍需按 README §7 全局质量要求跑一次后端 pytest + 前端 tsc/vitest/build + 全量 Playwright e2e（阶段一至六全部既有场景）。

## 7. 测试与验证命令

- 后端 pytest：`./.venv/bin/pytest tests/webui/ -q --ignore=tests/webui/e2e`（回归，若 §0 决策涉及代码改动需为其新增用例）。
- 前端：`npx tsc --noEmit` / `npx vitest run` / `npm run build`。
- Playwright e2e 全量：`./.venv/bin/pytest tests/webui/e2e/ --browser chromium -q`（阶段一至六全部既有场景，本阶段若无新场景则不新增测试文件，仅确认全部仍通过）。
- 若 §0.4 决定需要真实环境人工验收：记录具体验证的功能点、使用的真实凭证类型（不得在报告中明文记录密钥本身）、观察到的结果。

## 8. 验收标准

- §0 四个决策问题均已获得您的确认。
- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 阶段一至六回归验证仍全部通过（含全量 Playwright e2e）。
- 根 `README.md`/`CONTRIBUTING.md` 已更新，`pa_agent/gui/` 已加 legacy 说明。
- 已生成最终验收报告（覆盖 README §8 全部关键流程）。
- `docs/webui_migration/README.md` 顶部状态行更新为"已完成"。

## 9. 停止条件

- §0 四个决策问题未获得您确认前，不得开始实施。
- 若 §0.1 决定修复 `DecisionPanel.tsx`，发现影响范围超出这两个组件（例如需要连带修改 `/ws/analysis` 消息 schema 或阶段三/四已依赖的字段位置），须暂停并重新向您报告工作量评估，不得在"文档收尾"阶段顺带做大范围重构。
