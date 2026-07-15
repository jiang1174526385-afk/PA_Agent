# 阶段六执行方案：演示模式回放 + 下单机会通知

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-5-completion-report.md`](phase-5-completion-report.md)（状态 `complete`）
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段七内容（文档收尾与最终清理）。

## 0. 需要您决策的问题（实施 session 开始前应先确认，不得自行假设）

1. **演示模式的 WS/REST 接口设计**：总纲 §5 阶段六条目写"是否复用 `/ws/analysis`/`/ws/kline` 待定"。`DemoReplayer`（`pa_agent/demo/replayer.py`，116行）是一个 `QTimer` 驱动的定时器，按字符逐个"重放"一份已保存的 `AnalysisRecord`，发出与 `_AnalysisWorker` **相同**的信号集合（`reasoning_token`/`content_token`/`record_ready`/`status_update`/`finished`）——即桌面端把"演示模式"设计成"看起来和真实分析一模一样的假数据源"。这提示 Web 端可能不需要新端点，而是让 `/ws/analysis` 在"演示模式"下改为播放 `DemoReplayer` 而非调用真实 `TwoStageOrchestrator.submit`。但这需要确认：(a) 演示模式是否允许与真实分析共用同一个 `/ws/analysis` 连接（复用现有 `submit`/`cancel` 消息类型，新增一个 `mode: "demo"`？还是新增 `demo_record_id` 参数？）；(b) 演示记录从哪里选取（`records/` 目录下已保存的历史记录？还是需要新增一个"选择要回放的记录"的 REST 列表接口）；(c) 演示模式是否需要在 UI 上与真实分析明确区分视觉状态（桌面端有 `self._demo_mode` 标志位，阶段五总结报告确认它会跳过 `FreeChatSession` 创建、走不同的分支）。
2. **下单机会提醒的触发位置与呈现形式**：`pa_agent/gui/order_opportunity.py`（160行）的 `has_order_opportunity()`/格式化函数是纯函数（无 Qt 依赖，可直接复用），但触发它的调用点、弹窗展示方式（桌面端用 `QMessageBox`/系统托盘通知？需要在 `main_window.py` 里搜索调用点确认）需要先确认。Web 端候选方案：(a) 浏览器 `Notification` API（需要用户授权，页面需在前台或已授权后台通知）；(b) 页面内 toast/横幅（无需授权，但仅在页面打开时可见）。总纲 §5 阶段六条目提到"toast/声音"，需要与您确认是否需要真正的浏览器系统通知，还是页面内提醒即可。
3. **飞书/PushPlus 通知触发入口**：阶段一执行方案已明确"设置页只做 CRUD 不做通知触发"，`pa_agent/notify/feishu_notifier.py`（407行）/`pushplus_notifier.py`（171行）的实际推送逻辑本阶段"保持不变，仅新增触发入口"。需要确认触发时机：(a) 仅在下单机会检测到时自动触发（对应 `FeishuRead.notify_on_order_only` 字段，阶段一已有此设置项但从未被读取生效）；(b) 是否需要一个手动"测试推送"按钮（桌面端是否有等价功能，需要先搜索确认）。

## 1. 阶段目标

把以下桌面组件迁移为 Web 组件/服务，视觉沿用**阶段一暗色主题**：

- `pa_agent/demo/replayer.py`（116行）——`DemoReplayer`，定时器驱动的历史记录回放
- `pa_agent/gui/order_opportunity.py`（160行）——下单机会检测 + 提醒文案格式化
- `pa_agent/notify/feishu_notifier.py`（407行）/`pushplus_notifier.py`（171行）——飞书/PushPlus 实际推送，新增触发入口（推送逻辑本身不改）

## 2. 非目标

- 不实现阶段七的文档收尾/legacy 标注/最终清理。
- 不改动阶段二报告页面、阶段三决策树面板、阶段四流程图、阶段五自由对话/调试面板的任何代码。
- 不改动飞书/PushPlus 的推送实现细节（签名、请求格式、重试逻辑），只新增"何时调用"的触发点。
- 不改动 `pa_agent/orchestrator/two_stage.py`、`/ws/analysis` 既有消息 schema（除非 §0.1 决策要求复用同一连接新增 `mode`/`demo_record_id` 字段，此时改动仅限新增，不得删除/重命名既有字段——遵循阶段五 `/ws/analysis` 的兼容策略先例）。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-5-completion-report.md`。
2. `git status --short`，确认阶段五的改动已按用户要求处理，不得回滚。
3. **完整通读以下文件**（本执行方案只读了每个文件的开头片段/行数统计，未覆盖完整逻辑）：
   - `pa_agent/demo/replayer.py`（116行，`DemoReplayer` 的完整定时器调度逻辑：`_CHAR_MS`/`_STAGE_GAP_MS` 节奏、`finished`/`record_ready` 信号的触发顺序）
   - `pa_agent/gui/order_opportunity.py`（160行，`has_order_opportunity()` 之外的格式化函数、`confidence_threshold` 的读取来源）
   - `pa_agent/notify/feishu_notifier.py`（407行）/`pushplus_notifier.py`（171行）——推送函数签名、返回值、错误处理
   - `pa_agent/gui/main_window.py` 中搜索 `DemoReplayer`/`order_opportunity`/`feishu_notifier`/`pushplus_notifier` 的全部调用点，确认触发时机、演示模式标志位 `self._demo_mode` 的完整影响范围（阶段五总结报告 §8 已发现它会跳过 `FreeChatSession` 创建，还有哪些分支受影响需要完整确认）
4. 确认 §0 三个决策问题已经和您对齐。
5. 复用阶段三/四/五已确认的分工原则：格式化/业务规则留在 Python（`order_opportunity.py` 的纯函数、通知推送逻辑本身），几何/纯展示布局在前端实现。

## 4. 当前代码事实摘要（不完整，实施时必须重新通读全文核实）

- `DemoReplayer` 是 `QObject` 子类，用 `QTimer` 驱动，发出与桌面端 `_AnalysisWorker` 相同的信号名（`reasoning_token`/`content_token`/`record_ready`/`status_update`/`finished`）——这与阶段五确认的"`SessionTokenLedger` 虽是 QObject 但可以在无 QApplication 事件循环下安全使用（emit 无接收者时是无操作）"是同一类可复用性质，`DemoReplayer` 本身的调度算法（哪个 tick 该 emit 什么）大概率与 Qt 无关，只有 `QTimer` 触发机制需要替换为 asyncio 定时器/任务（参照总纲 §1 对 `RefreshLoop` 的处理方式：`RefreshBroadcaster` 已经是"心跳轮询 → WS 广播"的先例，可以直接类比"定时回放 → WS 广播"）。
- `order_opportunity.py` 已确认是纯函数（无 PyQt 依赖，`from PyQt6.QtCore import Qt` 这一行 import 需要在完整通读时确认是否真的被用到，如果只是未清理的死代码，Web 端可以直接 `import` 复用整个模块而不摘抄）。
- `FeishuRead.notify_on_order_only`/`PushPlusRead` 相关字段阶段一已经在设置 DTO 里存在（`pa_agent/webui/schemas/settings.py`），但从未被任何 Web 端逻辑读取生效——与阶段四总结报告 §7 记录的 `decision_flow_auto_play`/`decision_flow_play_seconds`"阶段一带过来但首次被阶段四实际使用"是同一种情况，本阶段是这些通知相关设置字段第一次被真正读取触发行为。

## 5. 实施步骤（骨架，实施 session 必须先完整读完 §3 列出的文件再据实调整/展开）

1. 完整通读 §3 列出的全部文件，梳理：`DemoReplayer` 的定时调度算法、`order_opportunity.py` 的完整 API、飞书/PushPlus 推送函数签名、`main_window.py` 里三者的全部调用点与 `self._demo_mode` 影响范围。
2. 根据 §0.1 的决策，设计演示模式的 WS/REST 接口（新端点或复用 `/ws/analysis` 新增 `mode`/`demo_record_id`）；如需要"选择要回放的历史记录"，设计一个只读的记录列表 REST 接口（读取 `records/` 目录）。
3. 后端：`pa_agent/webui/services/`（`DemoReplayer` 的 asyncio 等价物）+ `pa_agent/webui/api/`（演示模式端点、下单机会检测挂载点、通知触发挂载点）+ `pa_agent/webui/schemas/`（新增 DTO）。
4. 下单机会检测：在 `/ws/analysis` 收到 record 后（`analysis.py::_run()` 内，与阶段五 `build_chat_session()` 同一位置）调用 `has_order_opportunity()`，按 §0.2 决策的呈现形式推送到前端（新增 WS 消息类型或独立通道）。
5. 通知触发：在检测到下单机会时，按 §0.3 决策调用飞书/PushPlus 推送函数（复用 `pa_agent/notify/` 现有实现，只新增调用点，不改推送逻辑）。
6. 前端：`src/demo/`（记录选择 + 回放控制 UI，视觉复用阶段五 `ChatPanel`/阶段四 `DecisionFlowPanel` 的暗色面板风格）、`src/notify/`（下单机会提醒 toast，按 §0.2 决策决定是否接入浏览器 `Notification` API）。

## 6. 兼容策略与回滚点

- 新增代码位于 `pa_agent/webui/frontend/src/demo/`、`pa_agent/webui/frontend/src/notify/`；后端新增文件放在 `pa_agent/webui/services/`、`pa_agent/webui/api/`、`pa_agent/webui/schemas/` 对应位置，与阶段一/三/四/五的目录习惯一致。
- `pa_agent/demo/replayer.py`、`pa_agent/gui/order_opportunity.py`、`pa_agent/notify/feishu_notifier.py`、`pa_agent/notify/pushplus_notifier.py` 均不改动核心逻辑/推送实现。
- 若 §0.1 决定复用 `/ws/analysis`，改动限定为新增消息类型/字段（不删除/不重命名阶段一至五已有消息类型字段），保证既有 K线/分析/自由对话流程不受影响。
- **`.app-shell` 布局预算已经很紧张**（阶段五总结报告 §4 已记录：视口 720px 下 `.flow-row`(480px) + `.chat-debug-row`(约420px) 已经超出一屏，依赖 `min-height: 100vh` + 页面纵向滚动兜底）。本阶段如果在页面下方新增演示模式回放面板，必须意识到这一点，不要假设"一屏能装下所有区块"，实施后必须跑一次全量 Playwright e2e（覆盖阶段一至五全部既有场景，不只是本阶段新增场景）以确认没有引入同类回归——这是阶段五总结报告 §4 明确要求的经验教训。

## 7. 测试与验证命令

- 后端 pytest：`DemoReplayer` 的 asyncio 包装层、`has_order_opportunity()` 触发点、通知触发（mock 飞书/PushPlus 推送函数，不发起真实网络请求）的用例。
- 前端：`tsc --noEmit`/`npm run build`/`npx vitest run`（新增演示模式控制/下单提醒的纯展示逻辑单测）。
- Playwright e2e：`tests/webui/e2e/test_phase6_demo_notify_smoke.py`——选择一条历史记录回放并观察时间线/流式展示、下单机会提醒出现、（如可测试）通知触发调用被记录。
- **全量回归**：`./.venv/bin/pytest tests/webui/e2e/ --browser chromium -q`（阶段一至六全部场景），验证 §6 提到的布局预算问题未复现。

## 8. 验收标准

- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 阶段一/二/三/四/五回归验证仍全部通过（含全量 Playwright e2e）。
- 已生成 `phase-6-completion-report.md` 和 `phase-7-execution-plan.md`。

## 9. 停止条件

- §0 三个决策问题未获得您的确认前，不得开始实施。
- 通读 §3 列出的文件后，如果发现飞书/PushPlus 触发时机、演示模式与真实分析的接口复用方式，比本文件 §4 的摘要判断更复杂（例如推送函数有未预料到的副作用、需要处理网络失败重试），需要重新评估工作量并向您报告。
- 若发现下单机会通知需要真正的浏览器系统级通知权限，且这在无头/Playwright 测试环境下无法可靠验证，必须暂停并向您确认验收标准是否允许"仅验证页面内 toast，系统通知需人工验证"这种降级验证方式。
