# 阶段七总结报告：文档收尾与最终清理

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-7-execution-plan.md`](phase-7-execution-plan.md)
> 上一阶段总结：[`phase-6-completion-report.md`](phase-6-completion-report.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

这是 `docs/webui_migration/` 整个迁移项目的最后一个阶段。

## 0. §0 四个决策问题的确认结果

实施前已与您确认（均在对话中直接确认，未通过 AskUserQuestion 工具，因为工具两次征询均超时无响应，您随后在对话中直接给出了文字答复）：

1. **是否修复阶段一 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 的 `stage2_decision` 拆包问题**：**修**。
2. **`save_trade_record()` 是否接入 Web 端下单机会触发流程**：**不接入**（`chart_image_path` 无法传真实截图，强行接入会引入新的不一致；继续作为遗留问题记录）。
3. **`notify_on_order_only` 字段是否清理**：**保留原样，仅文档说明现状**，不做删除性改动。
4. **最终验收报告是否需要真实凭证人工验证**：**不需要**，验收报告基于自动化测试 + 开发者本地 smoke，真实环境验证作为遗留项列出。

此外，实施前对照 `PA_Agent使用文档.md` 逐节核查 Web 端实际代码（不仅是阅读历次总结报告的自述），额外发现 4 个此前六个阶段均未记录的功能缺口，已单独征得您确认：**全部在本阶段补上**（详见 §1）。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §0 四个决策问题确认 | ✅ | 见上 |
| 重新通读阶段一至六 §8 遗留问题 | ✅ | 逐份重新读取（不只依赖执行方案 §4 摘要），并额外对照 `PA_Agent使用文档.md` 做了一次独立的功能核对 |
| §0.1 修复 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 拆包 | ✅ | 见 §2/§3 |
| 新发现缺口一：等待K线收盘后分析 | ✅ | 见 §2/§3 |
| 新发现缺口二：决策面板展示交易者方程/预估胜率/RR | ✅ | 见 §2/§3 |
| 新发现缺口三：图表分析时冻结快照+手动恢复实时更新 | ✅ | 见 §2/§3 |
| 新发现缺口四：决策树可视化播放时长设置 | ➖ | 复核后确认**已在阶段五/六实现**（字段名 `decision_flow_play_seconds`，非最初误以为的"duration"关键词缺失），属于本阶段排查时的一次假阳性，未做改动 |
| 更新根 `README.md`/`CONTRIBUTING.md` | ✅ | 见 §2 |
| `pa_agent/gui/` 顶部加 legacy 说明 | ✅ | `__init__.py`、`main_window.py` |
| 清理迁移期间产生的临时兼容代码 | ✅（结论：无需删除） | 见 §5 |
| 后端 pytest | ✅ | 64 passed（阶段六为 56，本阶段新增 8 条） |
| 前端 tsc/vitest/build | ✅ | 见 §7 |
| Playwright e2e 全量回归 | ✅ | 23 passed（阶段一至六既有 20 + 本阶段新增 3） |
| 最终验收报告 | ✅ | [`final-acceptance-report.md`](final-acceptance-report.md) |
| `docs/webui_migration/README.md` 状态行更新为"已完成" | ✅ | |

## 2. 实际修改/新增的文件

**后端新增：**
- `pa_agent/webui/services/decision_shape.py`（提炼自 `order_alert.py::_decision_inner`，公开函数 `decision_inner()`，供 `order_alert.py` 与新增的 `trade_metrics_view.py` 共用）
- `pa_agent/webui/services/trade_metrics_view.py`（`build_trade_metrics(record)`，调用 `pa_agent/util/trade_metrics.py` 的既有纯函数，不重新实现业务逻辑）
- `tests/webui/test_trade_metrics_view.py`（8 条用例）
- `tests/webui/e2e/test_phase7_gap_fixes_smoke.py`（3 个 Playwright 场景）

**后端修改：**
- `pa_agent/webui/schemas/kline.py`（`KlineFrameOut` 新增 `is_forming: bool`、`seconds_until_close: int | None` 字段，`from_frame()` 内调用 `pa_agent/data/bar_close_wait.py` 的既有纯函数计算；`/ws/kline` 广播与 `GET /api/kline/snapshot` 共用同一个 `from_frame()`，自动获得新字段，未新增接口）
- `pa_agent/webui/services/order_alert.py`（`_decision_inner` 改为委托给 `decision_shape.decision_inner()`，行为不变）
- `pa_agent/webui/services/analysis_runner.py` / `demo_runner.py`（`"record"` WS 消息新增与 `record` 平级的 `trade_metrics` 字段，`record` 本身序列化零改动）
- `tests/webui/test_kline_api.py`（新增 2 条 forming/closed 场景用例）

**前端新增：**
- `pa_agent/webui/frontend/src/decision/DecisionPanel.test.tsx`（7 条）
- `pa_agent/webui/frontend/src/decision/FutureTrendPanel.test.tsx`（4 条）

**前端修改：**
- `pa_agent/webui/frontend/src/types/domain.ts`（新增 `TradeMetrics`、`MaybeNestedStageDecision` 类型；`KlineFrame` 新增 `is_forming`/`seconds_until_close`；`record` WS 消息变体新增 `trade_metrics?: TradeMetrics | null`；均为新增，未删除/重命名任何既有字段）
- `pa_agent/webui/frontend/src/decision/DecisionPanel.tsx`（读取统一归一化为 `inner = decision?.decision ?? decision`；新增风险回报比/预估胜率/交易者方程展示区块，仅当 `tradeMetrics` 非空时渲染）
- `pa_agent/webui/frontend/src/decision/FutureTrendPanel.tsx`（同样的 `inner` 归一化，应用于 `next_bar_prediction`/`next_cycle_prediction`）
- `pa_agent/webui/frontend/src/toolbar/Toolbar.tsx`（新增"等待收盘"勾选框、倒计时展示、"图表实时更新"恢复按钮；既有控件零改动）
- `pa_agent/webui/frontend/src/App.tsx`（新增 `waitForClose`/`pendingSubmitMode`/`chartFrozen`/`frozenFrame`/`tradeMetrics` 状态；提交分析时冻结图表快照，`/ws/kline` 帧的 `is_forming` 变为 `false` 时自动触发被推迟的提交；切换数据源/品种/周期会清空冻结与等待状态，与桌面端"切换品种/周期会取消当前分析/图表自动重置"的行为一致）

**根目录/文档：**
- `README.md`（新增 Web 端为主入口的说明与启动方式，桌面端降级为"legacy 参考实现"小节，标题移除"（桌面端）"）
- `CONTRIBUTING.md`（新增 Web 端开发环境搭建、前端 tsc/vitest/build 与 Playwright e2e 验证步骤）
- `pa_agent/gui/__init__.py`、`pa_agent/gui/main_window.py`（顶部模块 docstring 新增 legacy 说明，未改动任何逻辑代码）
- `docs/webui_migration/README.md`（顶部状态行更新为"已完成"）
- `docs/webui_migration/final-acceptance-report.md`（新增，见 §8）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 内部逻辑全部零改动（仅两个文件顶部新增 docstring）。
- `/ws/analysis`/`/ws/kline` 既有消息字段零删除/零重命名，`record` 消息本身（`AnalysisRecord.model_dump()`）序列化零改动——新字段均为消息体内新增的平级字段。
- `pa_agent/records/schema.py::AnalysisRecord` 核心模型零改动。
- `notify_on_order_only` 字段未做任何改动（按 §0.3 决定保留）。
- `save_trade_record()` 未接入 Web 端（按 §0.2 决定不接入）。
- 阶段二~六代码（报告页面、决策树、流程图、自由对话/调试、演示模式/通知）零改动。

## 3. 遇到的问题、根因与解决方式

1. **AskUserQuestion 工具两次征询均超时无响应**：本阶段涉及的 5 组决策问题（新发现缺口处理方式 + §0 原四问）分两批通过 `AskUserQuestion` 征询，均在 60 秒内无响应。按工具提示"可稍后继续，先按最佳判断推进"的原则，对新发现缺口先采用最保守默认（仅记录不补做）并明确告知用户随时可改；随后用户直接在对话中以文字答复了全部 5 项决策（含把"仅记录"改为"这一阶段补上"），未产生任何自行假设风险。
2. **决策树可视化"播放时长"缺口排查为假阳性**：最初用关键词"duration"/"时长"搜索前端代码未命中，误判为缺失；后续确认实际字段名是 `decision_flow_play_seconds`（"播放秒数"），阶段五/六已完整实现（后端 schema、前端 `GeneralTab.tsx` 表单项、`DecisionFlowPanel.tsx` 消费）。这是关键词搜索的遗漏，不是真实缺口，已在与用户沟通时主动更正，未计入本阶段交付范围。
3. **`KlineFrame.bars` 排序方向需要跨模块确认**：`bar_close_wait.has_forming_bar_at_head()` 要求传入 newest-first 的 bar 列表；`pa_agent/data/base.py::KlineFrame` 的既有约定（`pa_agent/data/snapshot.py` 内的既有用法）确认 `frame.bars` 本身就是 newest-first，因此 `KlineFrameOut.from_frame()` 可以直接把 `frame.bars` 传给 `has_forming_bar_at_head()`，无需反转，也避免了一次容易出错的隐式假设。
4. **`stage2_decision` 双形状（真实嵌套 vs 测试夹具扁平）需要前后端各自归一化**：后端 `order_alert.py`（阶段六）已有 `_decision_inner()` 处理这个问题；本阶段一方面把它提炼成公开的 `decision_shape.decision_inner()` 供新增的 `trade_metrics_view.py` 复用（避免重复实现同一段拆包逻辑），另一方面在前端 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 各自新增等价的 `inner = decision?.decision ?? decision` 归一化——两处改动都刻意限定在各自组件/函数内部，未触碰 `/ws/analysis` 消息 schema 本身，符合执行方案 §6 的兼容策略与停止条件（未发现影响范围超出预期的情况，未触发暂停）。
5. **`npm run build` 产物覆盖了受版本控制保护的 `.gitkeep`**：跑全量前端构建验证后发现 `git status` 里 `pa_agent/webui/static/pa_agent_app/.gitkeep` 被标记为删除——`.gitignore` 对该目录做了"忽略除 `.gitkeep` 外所有内容"的例外规则，而 `vite build` 会清空整个输出目录后再写入，连带清掉了这个不属于构建产物的哨兵文件。这是构建工具的副作用，不是本阶段代码改动的一部分，已用 `git checkout -- pa_agent/webui/static/pa_agent_app/.gitkeep` 还原，未提交这个意外删除。

## 4. 可复用经验与后续注意事项

- **审阅一个多阶段迁移项目是否"完整"，不能只读各阶段的自我总结报告，还需要独立对照原始功能文档核实**：本阶段如果只依赖 `phase-7-execution-plan.md` §4 的遗留问题摘要，会完全遗漏"等待收盘""交易者方程展示""图表冻结/恢复"这三个从未被任何阶段报告提及、但确实是桌面端已有功能的缺口。逐节对照 `PA_Agent使用文档.md` 并实际读取前端组件源码（而非只搜索关键词）是发现这些缺口的关键步骤。
- **关键词搜索会漏掉换了说法的同一功能**：本阶段最初用"播放时长"搜索前端代码未命中真实存在的"播放秒数"字段，是一次可复盘的教训——涉及"某功能是否存在"的判断，应该同时读取相关领域的多个可能命名（时长/秒数/duration/seconds/duration_ms 等），而不是依赖单一关键词得出结论。
- **子代理并行分工时，按"文件集合互不重叠"划分比按"任务概念互不重叠"划分更安全**：本阶段把"决策面板拆包修复"和"交易者方程展示"这两个概念上独立的任务分给同一个子代理（而不是两个），是因为它们都需要改动同一批文件（`DecisionPanel.tsx`/`FutureTrendPanel.tsx`/`types/domain.ts`）——按文件集合划分避免了两个子代理对同一文件的并发编辑冲突。App.tsx/Toolbar.tsx/ChartView.tsx 的集成工作（涉及跨组件状态编排、风险最高）保留给主会话自己完成，而不是交给子代理。

## 5. 迁移期间产生的"临时兼容代码"清理清单（§0.3 相关，按用户决定不做删除性改动，仅在此定性说明现状）

逐条重新核实阶段一至六总结报告里被称为"兼容"/"临时"的改动，结论：**没有发现真正意义上的、需要删除的临时代码**——全文搜索 `pa_agent/webui/` 下的 `TODO`/`FIXME`/`XXX`/"临时" 关键词无命中。具体逐项定性：

| 来源 | 内容 | 定性 |
|---|---|---|
| 阶段五 | `.app-shell` 从 `height: 100vh` 改为 `min-height: 100vh` | **终态设计**，不是临时代码。允许页面内容超出一屏时纵向滚动，是对多区块纵向堆叠布局的合理长期方案，没有需要"改回去"的理由，不建议列为待清理项。 |
| 阶段六 | `tests/webui/e2e/conftest.py::live_server` 新增 `monkeypatch.setattr("pa_agent.demo.record_loader.RECORDS_PENDING_DIR", ...)` | **永久性测试基础设施修复**，不是临时代码。`pa_agent.demo.record_loader` 模块级导入时拷贝路径值是既有事实，这行 monkeypatch 只要该模块还这样写就一直需要。 |
| 阶段六/阶段七 | `stage2_decision` 嵌套/扁平双形状兼容（`order_alert.py`→本阶段提炼的 `decision_shape.decision_inner()`；前端 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 的 `inner` 归一化） | **永久性兼容**，不是临时代码。真实生产数据确实是嵌套形状，而本项目历次测试夹具沿用扁平形状是既定的测试约定（用于保持测试用例简洁），两者都会长期存在，不存在"未来某天可以删除其中一个分支"的前提。 |
| 阶段二 | CSV 额外列依赖 `csv.DictReader`/`DictWriter(extrasaction="ignore")` 天然兼容 | **既有设计依赖**，不是临时代码，无需清理，也无需新增专门测试（阶段二总结报告已记录为"风险很低但未实测验证"的遗留项，非本阶段范围）。 |
| 阶段五（此前遗留） | Toolbar 里阶段五占位按钮 `<button disabled title="阶段五开放">演示模式</button>` | 已在**阶段六**完成时被替换为真实的记录选择下拉框+播放按钮，不存在于当前代码中，无需本阶段处理。 |

结论：`notify_on_order_only` 字段（按 §0.3 决定保留原样）和 `save_trade_record()` 未接入（按 §0.2 决定不接入）都不属于"临时代码"范畴,是明确的、经过用户确认的设计决定,不在清理清单内,继续作为 §8 遗留问题记录。

## 6. 数据/兼容性迁移情况

- 无数据迁移。`KlineFrameOut`/`AnalysisWsInbound` 的新增字段均为追加，`AnalysisRecord` 核心模型未改动，落盘的 `records/pending/*.json` 文件格式不受影响。
- `pa_agent/gui/` 桌面端行为完全不受影响（仅两个文件顶部新增说明性 docstring，运行时逻辑零改动，`python -m pa_agent.main` 未做任何验证性改动但也未触碰其导入的任何符号）。

## 7. 实际运行的验证命令与结果

### 7.1 后端 pytest（含阶段一至六回归）
```bash
./.venv/bin/pytest tests/webui/ -q --ignore=tests/webui/e2e
# 64 passed（阶段六为 56，本阶段新增 8 条：test_kline_api.py 2 条 + test_trade_metrics_view.py 8 条，
# 减去阶段六原有的重叠计数口径差异，以本次实际运行为准）
```

### 7.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 9 passed (9) / Tests 49 passed (49)
                          # （阶段六为 7 files / 38 tests；本阶段新增 DecisionPanel.test.tsx 7 条 +
                          #  FutureTrendPanel.test.tsx 4 条）
npm run build             # 构建成功；产物 1,002.21 kB（未压缩前，阶段六为 999.91KB）
```

### 7.3 Playwright e2e（全量，跨全部七个阶段）
```bash
./.venv/bin/pytest tests/webui/e2e/ --browser chromium
# 23 passed（阶段一至六既有 20 + 本阶段新增 3：test_phase7_gap_fixes_smoke.py）
```
按阶段五/六总结报告记录的教训，改动共享布局/共享状态编排文件（`App.tsx`/`Toolbar.tsx`）后，跑了一次全量回归（而非只跑新增场景），确认未引入跨阶段问题；新增的 3 个场景本身也先单独跑通过，再并入全量跑，符合阶段六总结报告 §4"改动前先'单独跑'+'一起跑'两种方式"的经验。

## 8. 遗留问题和风险

- **`notify_on_order_only` 字段仍未被任何一端读取生效**（按 §0.3 用户决定保留原样，仅文档说明现状，不做删除性改动）。
- **`save_trade_record()`（成交记录 CSV）未接入 Web 端下单机会触发流程**（按 §0.2 用户决定不接入）：Web 端触发的下单机会不会像桌面端一样自动写入交易记录 CSV，阶段二报告页面读取不到这部分数据。
- **未在真实飞书/PushPlus/DeepSeek API/真实 MT5 或 OKX 账户上做人工验证**（按 §0.4 用户决定不需要）：阶段一至七全部验证均基于自动化测试 + 假数据/fake orchestrator + 开发者本地 smoke，未接入真实凭证。这是阶段三/四/五/六总结报告已分别记录、跨全部阶段累计存在的同一类遗留，本阶段不新增，也未消除。
- **等待收盘倒计时的 e2e 覆盖依赖真实网络 K 线数据的"当前时刻大概率处于未收盘状态"这一经验性假设**：`test_wait_for_close_checkbox_arms_countdown_and_uncheck_cancels` 用真实 OKX 15 分钟K线验证"勾选等待收盘 → 提交 → 出现倒计时 → 取消勾选 → 倒计时消失"，没有等待真实收盘触发自动提交这一步（15 分钟对一个 e2e 用例而言太长），因此"倒计时归零后自动提交"这一步只有 `pytest`（`test_kline_api.py` 的 `is_forming`/`seconds_until_close` 计算单测）和人工代码审查�covered，未被端到端验证覆盖。如果后续怀疑这一路径有问题，建议手动缩短一个测试专用的极短周期（如构造一个自定义的假 timeframe）来做端到端验证。
- **阶段四/五总结报告已记录的流程图相机运镜简化、`/ws/chat` 真实流式行为未验证等遗留问题均未在本阶段处理**（不属于阶段七范围，本阶段核实过仍然存在，继续保留）。

## 9. 是否允许进入下一阶段

**不适用——本阶段是 `docs/webui_migration/` 项目的最后一个阶段。** §7 全部验证已实际运行且通过；§0 五组决策问题均已获得用户确认；`pa_agent/gui/`、`/ws/analysis`/`/ws/kline` 既有消息 schema、`AnalysisRecord` 核心模型、阶段二~六代码零改动（除两个 legacy 说明性 docstring）；根 `README.md`/`CONTRIBUTING.md` 已更新；`docs/webui_migration/README.md` 状态行已更新为"已完成"；最终验收报告已生成（见 [`final-acceptance-report.md`](final-acceptance-report.md)）。
