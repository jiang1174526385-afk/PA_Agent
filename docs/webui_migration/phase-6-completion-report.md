# 阶段六总结报告：演示模式回放 + 下单机会通知

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-6-execution-plan.md`](phase-6-execution-plan.md)
> 上一阶段总结：[`phase-5-completion-report.md`](phase-5-completion-report.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

## 0. §0 三个决策问题的确认结果

实施前已通过 AskUserQuestion 向您确认（均采纳推荐项）：

1. **演示模式 WS/REST 接口设计**：复用 `/ws/analysis`，`submit` 消息新增 `mode: "demo"` + `demo_record_id` 字段；记录来源新增只读列表接口 `GET /api/demo/records`（读取 `records/pending/` 目录，`is_demo_playable()` 过滤）。
2. **下单机会提醒呈现形式**：仅页面内 toast（`OrderOpportunityToast`），不接入浏览器 Notification API，不加声音提示。
3. **飞书/PushPlus 通知触发时机**：与桌面端行为完全一致——仅下单机会触发（`has_order_opportunity()` + `alert_on_order_opportunity` 设置），演示模式回放同样会触发真实推送，不做特殊屏蔽。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §3 完整通读 4 个文件 + `main_window.py` 调用点 | ✅ | `replayer.py`(116行)/`order_opportunity.py`(160行)/`feishu_notifier.py`(407行)/`pushplus_notifier.py`(171行) 全部通读；`main_window.py` 中 `DemoReplayer`/`order_opportunity`/`feishu_notifier`/`pushplus_notifier`/`_demo_mode` 全部调用点（§2400-3950 区间）逐一确认 |
| §5.2 演示模式 WS/REST 接口 | ✅ | `/ws/analysis` 新增 `mode="demo"` 分支；`GET /api/demo/records` |
| §5.3 `DemoReplayer` 的 asyncio 等价物 | ✅ | `pa_agent/webui/services/demo_runner.py::DemoRunner` + `build_demo_steps()`（逐字符/逐阶段调度算法与桌面端 `_build_steps` 完全对应） |
| §5.4 下单机会检测挂载点 | ✅ | `pa_agent/webui/services/order_alert.py::maybe_alert_order_opportunity()`，在 `analysis.py::_run()`/`_run_demo()` 的 record 产生后调用，与阶段五 `build_chat_session()` 同一位置 |
| §5.5 通知触发 | ✅ | `_spawn_notify()`（后台线程），复用 `pa_agent/notify/feishu_notifier.py`/`pushplus_notifier.py` 现有推送函数，签名/重试/请求格式零改动 |
| §5.5 前端 `src/demo/`、`src/notify/` | ✅（见 §5 设计偏离说明） | `src/demo/demoFormat.ts`（记录标签格式化）；`src/notify/OrderOpportunityToast.tsx`；记录选择+播放控件并入 Toolbar（见 §5） |
| 后端 pytest | ✅ | `test_demo_api.py`(2)/`test_demo_ws.py`(5)/`test_order_alert.py`(6)/`test_analysis_order_opportunity.py`(1)，共 14 条新增 |
| 前端 tsc/vitest/build | ✅ | 见 §7 |
| Playwright e2e | ✅ | `tests/webui/e2e/test_phase6_demo_notify_smoke.py`（2 场景） |
| 全量回归（阶段一至六） | ✅ | 20 个 e2e 场景全部通过 |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段七执行方案 | ✅ | [`phase-7-execution-plan.md`](phase-7-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增：**
- `pa_agent/webui/schemas/demo.py`
- `pa_agent/webui/api/demo.py`
- `pa_agent/webui/services/demo_runner.py`
- `pa_agent/webui/services/order_alert.py`
- `pa_agent/webui/frontend/src/demo/{demoFormat.ts,demoFormat.test.ts}`
- `pa_agent/webui/frontend/src/notify/OrderOpportunityToast.tsx`
- `tests/webui/test_demo_api.py`
- `tests/webui/test_demo_ws.py`
- `tests/webui/test_order_alert.py`
- `tests/webui/test_analysis_order_opportunity.py`
- `tests/webui/e2e/test_phase6_demo_notify_smoke.py`

**修改：**
- `pa_agent/webui/deps.py`（`AppState` 新增 `demo_runner: DemoRunner` 字段，`default_factory`，未删除/未重命名既有字段）
- `pa_agent/webui/api/analysis.py`（`ws_analysis()` 新增 `active_mode` 局部变量区分 `analysis`/`demo`，`cancel` 按当前模式路由到对应 runner；新增 `_run_demo()`；`_run()` 结尾新增 `await maybe_alert_order_opportunity(...)`；既有 `full`/`incremental` 消息类型/字段零改动）
- `pa_agent/webui/server.py`（新增 `demo_api.router` 挂载，其余路由挂载顺序未变）
- `pa_agent/webui/frontend/src/types/domain.ts`（`AnalysisWsInbound` 新增 `demo_finished`/`order_opportunity` 变体；`AnalysisWsSubmit.mode` 新增 `"demo"` 分支 + 新增 `demo_record_id` 可选字段；新增 `DemoRecordSummary`/`DemoRecordListResponse`；均为新增，未删除/重命名既有字段）
- `pa_agent/webui/frontend/src/api/paAgentApi.ts`（新增 `fetchDemoRecords()`）
- `pa_agent/webui/frontend/src/toolbar/Toolbar.tsx`（把阶段五遗留的禁用占位按钮 `<button disabled title="阶段五开放">演示模式</button>` 替换为记录选择下拉框 + 播放按钮 + 随机播放按钮；其余控件零改动）
- `pa_agent/webui/frontend/src/App.tsx`（新增 `demoRecords`/`demoRecordId`/`demoRunning`/`orderAlert` 状态；`useAnalysisSocket` 回调新增 `demo_finished`/`order_opportunity` 分支；新增 `handlePlayDemo`/`handlePlayRandomDemo`；`record` 分支追加一次 `fetchDemoRecords()` 刷新；渲染层追加 `<OrderOpportunityToast>` 条件渲染；阶段一/三/四/五既有布局元素零改动）
- `pa_agent/webui/frontend/src/styles/app.css`（新增 `.order-opportunity-toast*` 类，`position: fixed` 覆盖层，不占用 `.app-shell` 纵向布局预算；未新增色值，复用 `tokens.css` 的 `--warning`）
- `tests/webui/e2e/conftest.py`（`live_server` fixture 新增一行 `monkeypatch.setattr("pa_agent.demo.record_loader.RECORDS_PENDING_DIR", records_dir)`，原因见 §3 第 2 条）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 全部零改动（`git status --short -- pa_agent/gui/` 确认为空）。
- `pa_agent/demo/replayer.py`、`pa_agent/gui/order_opportunity.py`、`pa_agent/notify/feishu_notifier.py`、`pa_agent/notify/pushplus_notifier.py` 核心逻辑零改动（`order_opportunity.py` 被直接 `import` 复用 `has_order_opportunity`/`format_order_alert_message`；`replayer.py` 未被 import，其调度算法在 `demo_runner.py` 中按 Web 消息格式重新表达，因为原文件的输出是 Qt 信号而非 JSON 消息，无法直接复用，属于执行方案 §4 已预告的"只有 `QTimer` 触发机制需要替换"）。
- `/ws/analysis` 既有消息类型字段（`event`/`stage1_reasoning`/`stage1_content`/`stage2_reasoning`/`stage2_content`/`stage_prompt`/`stage2_files`/`record`/`error`）零改动，`submit`/`cancel` 既有字段零改动。
- 阶段二报告页面、阶段三决策树面板、阶段四流程图、阶段五自由对话/调试面板代码零改动。
- `pa_agent/records/trade_logger.py::save_trade_record()` 未接入 Web 端（见 §8 遗留问题）。

## 3. 遇到的问题、根因与解决方式

1. **`stage2_decision` 的真实生产形状是 `{"decision": {order_type, ...}, "decision_trace": [...], ...}`（嵌套），而本迁移项目自阶段一起所有 webui 测试夹具（`tests/webui/conftest.py::_make_record`、`e2e/conftest.py::_build_record`）使用的是扁平形状（`order_type` 直接在顶层，无 `decision` 嵌套）**：通读 `pa_agent/ai/prompt_assembler.py` 的阶段二输出契约（`"decision": {"order_direction": ..., "order_type": ...}`）、`pa_agent/orchestrator/two_stage.py` 实际赋值（`"stage2_decision": stage2_json`，`stage2_json` 是未拆包的原始 AI JSON）、`pa_agent/ai/decision_tree.py::build_stage2_gate_wait_response()`（同样嵌套）三处后确认：桌面端 `main_window.py::_bind_decision_tree` 是通过 `decision_inner = stage2_full.get("decision")` 拆包后才传给 `_has_order_opportunity()` 的。这意味着阶段一遗留的 `DecisionPanel.tsx`（直接读取 `decision.order_type`，无拆包）在真实生产数据下可能无法正确显示，但这是阶段一范围的既有问题，不在本阶段修复范围内（用户明确要求"不改动...任何代码"的清单不含阶段一 `DecisionPanel.tsx`，但改动它超出本阶段"演示模式+下单通知"的目标，属于独立议题）。为了让**我的新代码**同时正确处理"真实生产的嵌套形状"和"本项目既有测试夹具的扁平形状"两种已确认存在的真实情况，`order_alert.py::_decision_inner()` 优先尝试 `.get("decision")`，若不存在则回退为直接使用整个 `stage2_decision` 字典——已用两种形状各写一条 pytest 覆盖（`test_order_alert.py`）。
2. **e2e 全量回归里"单独运行阶段六第二个场景通过、但整个阶段六文件一起跑第二个场景失败"**：定位到 `pa_agent/demo/record_loader.py` 用 `from pa_agent.config.paths import RECORDS_PENDING_DIR` 在模块导入时把路径值拷贝进自己的模块全局命名空间；而 `tests/webui/e2e/conftest.py::live_server` fixture 只 monkeypatch 了 `pa_agent.config.paths.RECORDS_PENDING_DIR` 属性本身，没有同时 patch `pa_agent.demo.record_loader.RECORDS_PENDING_DIR` 这份"导入时拷贝"。由于 `pa_agent.demo.record_loader` 模块在进程内只会被首次导入一次（Python 模块缓存），第一个测试导入它时绑定的 tmp 目录会一直残留到同进程后续所有测试，导致后面的测试看到"别的测试残留在磁盘上的旧演示记录文件"。根因确认：单独跑该测试文件的第二个用例（不受污染）能过，两个一起跑必现。修复：在 `live_server` fixture 里追加一行 `monkeypatch.setattr("pa_agent.demo.record_loader.RECORDS_PENDING_DIR", records_dir)`（`tests/webui/test_demo_api.py` 里我自己新写的单元测试从一开始就同时 patch 了两处，未受影响）。这是阶段六首次让 webui 引用 `pa_agent.demo.record_loader`，此前阶段没有触发过这个陷阱，因此判断为"当前阶段需要的小范围兼容修改"，改动范围仅限于共享测试夹具新增一行 monkeypatch，未改动任何生产代码或其他阶段的测试文件。
3. **`pa_agent/gui/toolbar` 里阶段五遗留了一个禁用占位按钮**（`<button disabled title="阶段五开放">演示模式</button>`）：通读 `Toolbar.tsx` 时发现这个占位按钮，且其位置（工具栏内，与"提交分析"/"增量分析"并列）与执行方案 §5 建议的"新增 `src/demo/` 面板"存在设计张力——若在页面下方再加一个演示模式面板行，会直接撞上阶段五总结报告 §4 明确记录的"`.app-shell` 布局预算已经很紧张"的风险。占位按钮的存在表明更早的 session 已经预留了"演示模式功能应该做在工具栏里"的设计位置。综合判断后选择**不新增纵向布局行**，而是把记录选择下拉框 + 播放按钮 + 随机播放按钮直接并入工具栏，复用该占位按钮的位置——零新增纵向空间，从根源上避免了同类布局回归风险（而不是"小心翼翼地加一行还可能出问题"）。下单机会 toast 则用 `position: fixed` 悬浮层（与阶段五 `ValidationDialog` 的悬浮层模式一致），同样不占用 `.app-shell` 纵向预算。全量回归 20 个场景（含阶段一至五既有的 18 个）全部通过，未复现布局回归。
4. **`DemoReplayer`（Qt 版）本身无法直接 `import` 复用**：它是 `QObject` 子类，`__init__` 依赖 `QTimer`/`pyqtSignal`，在无 `QApplication` 事件循环的 FastAPI 进程里实例化本身可能没问题（阶段五总结报告确认过 `SessionTokenLedger` 这类 QObject 在无事件循环时 emit 是无操作），但它的调度机制（`QTimer.singleShot` 递归回调）与 asyncio 的协作式调度模型不兼容，无法简单包一层。因此按执行方案 §4 预告的方式处理：把 `_build_steps()` 的**调度算法**（`_CHAR_MS`/`_STAGE_GAP_MS` 节奏、字符级流式、阶段顺序）原样搬到 `demo_runner.py::build_demo_steps()`，但每一步产出的是 `/ws/analysis` 的 JSON 消息而非 Qt 信号；復用了同一份 `_prompt_parts()`/`content_from_response()`/`reasoning_from_response()` 辅助函数（后两者直接从 `pa_agent.ai.response_extract` 导入复用，未复制实现）。

## 4. 可复用经验与后续注意事项

- **改动共享测试基础设施（`conftest.py` fixture）前，先跑"新场景单独跑 + 和同文件其它场景一起跑"两种方式**：本阶段的 `RECORDS_PENDING_DIR` 污染问题只有在两个场景顺序跑时才会暴露，单独跑永远是绿的，容易被误判为"测试写对了"。
- **在多阶段共享的 Web 迁移项目里，"直接 `import` 复用桌面端纯函数模块"和"复用桌面端类的调度算法但重写通信层"是两种不同粒度的复用**：`order_opportunity.py`（纯函数，无 Qt 状态）可以整体 `import`；`DemoReplayer`（Qt 状态机 + 信号）只能复用其算法思路，通信层必须重写。判断标准是"这个模块的构造函数/方法是否依赖 Qt 事件循环或产生 Qt 信号"。
- **发现阶段一遗留的潜在 bug（`DecisionPanel.tsx` 未拆包 `stage2_decision.decision`）不代表要顺手修**：本阶段选择"让新代码同时兼容两种已确认存在的真实数据形状"，而不是趁机修改阶段一代码——遵循 README §3.2"当前阶段需要的小范围兼容修改可以实施，但必须在总结报告中说明原因"，已在 §3 第 1 条记录，供阶段七或独立议题评估是否需要修复阶段一 `DecisionPanel.tsx`（详见 §8）。
- **工具栏里的"禁用占位按钮 + title 提示未来阶段实现"是一个有用的线索**：本阶段能顺利判断"演示模式控件应该做进工具栏而非新面板"，很大程度上是因为读到了阶段五（或更早）留下的占位按钮和它的位置。如果阶段七盘点遗留问题时发现类似占位符，应优先读它的位置/title 提示，而不是凭空设计新布局。

## 5. 设计决策与偏离原计划的原因

- **前端"记录选择 + 回放控制"UI 并入 `Toolbar.tsx`，而非执行方案 §5 建议的独立 `src/demo/` 面板组件**：执行方案原文只是"建议"（"视觉复用阶段五 ChatPanel/阶段四 DecisionFlowPanel 的暗色面板风格"），具体信息架构留给实施时确认；本阶段发现阶段五已在工具栏预留占位按钮，且执行方案生成时的阶段五总结报告已明确警告"`.app-shell` 布局预算很紧张，阶段六如果还要在页面下方新增区块，必须先确认"——综合判断"零新增纵向空间"优于"新增一个可能引发回归的面板"，故改为工具栏内联控件。纯格式化逻辑仍按约定放进独立的 `src/demo/demoFormat.ts` 并配套单测，符合"格式化/业务规则用可测函数、几何/展示在组件里"的分工原则。
- **`GET /api/demo/records` 只返回 `is_demo_playable()` 为真的记录，不返回不可回放的记录（哪怕带 `playable: false` 标记）**：桌面端"自动随机"模式本来就只从可回放记录里选；"手动选择"模式虽然弹文件对话框允许选任意文件，但选中不可回放记录后会立刻弹窗提示并自动切换到其它可用记录（`main_window.py:2434-2444`）。Web 端由于文件选择变成了服务端提供的下拉列表，直接在列表层面过滤掉不可回放记录，相当于把桌面端"选了才发现不行、自动重选"的两步操作合并成"一开始就不会选到不行的"，效果一致且更简单，未额外实现"选中后失败重试"的分支。
- **未实现 `notify_on_order_only` 字段的读取生效**：该字段在阶段一的设置 DTO 里就存在，桌面端 `_spawn_post_order_followup` 从未读取它——本阶段严格复刻桌面端"仅下单机会触发"这一单一行为，未引入这个从未生效过的字段，避免创造一个"设置了但两端都不生效"之外的新状态（设置了但只有 Web 端生效，桌面端仍不生效，制造双端行为分裂）。这与 phase-6-execution-plan.md §4 的既有记录一致。
- **未接入 `pa_agent/records/trade_logger.py::save_trade_record()`**：桌面端 `_spawn_post_order_followup` 在下单机会触发时，除了发通知，还会把成交记录写入 `trade_records/*.csv`（供阶段二报告页面读取）。执行方案 §1 主要交付列表和 §0.3 决策问题都只提到"通知触发入口"，未把 CSV 记录接入列为本阶段交付项，我也未在 §0 决策阶段就此提问；为避免超出已确认范围自行扩大交付，本阶段未实现这部分，作为遗留问题记录在 §8，供您决定是否补做（可能需要用户提供的图表截图能力目前 Web 端也不存在，`chart_image_path` 因此传 `None`）。

## 6. 数据/兼容性迁移情况

- 无数据迁移：`pa_agent/demo/replayer.py`、`pa_agent/gui/order_opportunity.py`、通知模块均未改动，Web 端只是新增了驱动/调用它们的异步包装层。
- `AppState.demo_runner` 是新增的、`default_factory` 默认值字段，不影响任何既有序列化路径。
- `AnalysisWsInbound`/`AnalysisWsSubmit` 新增的消息类型/字段均为追加，未删除/重命名任何既有字段。

## 7. 实际运行的验证命令与结果

### 7.1 后端 pytest（含阶段一至五回归）
```bash
./.venv/bin/pytest tests/webui/ -q --ignore=tests/webui/e2e
# 56 passed（阶段一至五既有 42 条 + 本阶段新增 14 条：test_demo_api.py 2 条 /
# test_demo_ws.py 5 条 / test_order_alert.py 6 条 / test_analysis_order_opportunity.py 1 条）
```

### 7.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 7 passed (7) / Tests 38 passed (38)（本阶段新增 demoFormat.test.ts 2 条）
npm run build             # 构建成功；产物 999.91 kB（未压缩前，阶段五为 998.03KB，新增约 1.9KB）
```

### 7.3 Playwright e2e（全量，跨全部六个阶段）
```bash
./.venv/bin/pytest tests/webui/e2e/ --browser chromium -q
# 20 passed（阶段一 1 + 阶段二 X + 阶段三 2 + 阶段四 3 + 阶段五 3 + 阶段六 2）
```
按阶段五总结报告 §4 的教训要求，改动共享布局/共享测试夹具（`app.css`、`e2e/conftest.py`）后均触发过一次全量回归，确认未引入跨阶段问题。

## 8. 遗留问题和风险

- **`DecisionPanel.tsx`（阶段一）可能未正确拆包真实生产的嵌套 `stage2_decision.decision` 形状**：详见 §3 第 1 条。本阶段的新代码（`order_alert.py::_decision_inner()`）已确认能同时正确处理两种形状，不受此影响；但如果阶段一的展示面板确实有此问题，会导致真实分析（非本项目 e2e 假数据）下"决策"标签页可能显示不全。建议作为独立议题排查，不属于阶段六范围。
- **`notify_on_order_only` 字段仍未被任何一端读取生效**：详见 §5 第三条。字段本身的存在没有变化，只是继续保持"两端都不生效"的一致状态。
- **`save_trade_record()`（成交记录 CSV）未接入 Web 端下单机会触发流程**：详见 §5 第四条，导致 Web 端触发的下单机会不会像桌面端一样自动写入交易记录 CSV（阶段二报告页面读取的数据源）。如果这是重要功能缺口，建议作为阶段七或独立议题排期。
- **未在真实飞书/PushPlus 环境上验证过推送成功路径**：pytest/e2e 均 mock 了 `send_order_signal`/`pushplus_is_active`，未真实发起过网络请求（与阶段三/四/五总结报告记录的"未在真实 API 上验证流式行为"是同一类遗留）。建议您在配置了真实 webhook_url/token 的环境下手动触发一次下单机会，人工核对飞书卡片/PushPlus 消息的实际渲染效果。
- **随机演示按钮的"随机"实现是纯前端 `Math.random()` 从已加载的列表里选一条**，不是像桌面端 `pick_playable_demo_record()` 那样在服务端"排除上一条、优先带决策树可视化数据的记录"这类更精细的选择策略。当前 Web 端记录数量较少时体验上差异不大，如果 `records/pending/` 记录量很大导致下拉框难用，可能需要独立提出"服务端随机接口 + 更精细排除策略"的改进。

## 9. 是否允许进入下一阶段

**允许**。§7 全部验证已实际运行且通过（后端 56 passed、前端 tsc/vitest/build 均通过、Playwright e2e 全量 20 场景通过，含本阶段引入又立即修复的共享测试夹具问题）；阶段一至五回归全部通过；`pa_agent/gui/`、`pa_agent/demo/replayer.py`、`pa_agent/gui/order_opportunity.py`、`pa_agent/notify/*`、`/ws/analysis` 既有消息 schema、阶段二/三/四/五代码零改动；`phase-7-execution-plan.md` 已生成。
