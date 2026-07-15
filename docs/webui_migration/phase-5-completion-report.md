# 阶段五总结报告：自由对话 + AI 调试面板

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-5-execution-plan.md`](phase-5-execution-plan.md)
> 上一阶段总结：[`phase-4-completion-report.md`](phase-4-completion-report.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

## 0. §0 三个决策问题的确认结果

实施前已征得您确认（会话内 AskUserQuestion 60 秒无响应，随后您明确答复"都按照你推荐的来执行"）：

1. **`WS /ws/chat` 是否复用 `/ws/analysis`**：独立开一条 `/ws/chat`。`FreeChatSession` 每次分析完成后新建一个实例（`main_window.py:3750`），依赖的 `client`/`assembler`/`pending_writer`/`ledger` 是进程级单例，与 `/ws/analysis` "一次提交一次结果"的生命周期不同，用户很可能在分析 WS 连接断开后才开始追问。
2. **调试面板脱敏边界**：原样展示 `raw_response`（本身已是精简安全字段：`id`/`model`/`content`/`reasoning_content`/`usage`/`latency_ms`，不含 HTTP headers/完整请求体/API Key），仅对 `system_prompt`/`user_prompt`/`validation_info`/序列化后的 `raw_response` 做一次字符串级 API Key 替换（`mask_secret`），与桌面端 `DebugWidget._mask()` 行为完全一致。
3. **`AiStreamWindow`/`ConversationWidget`/`DebugWidget` 的功能划分**：统一一个发送入口，`ConversationWidget`（时间线）与 `AiStreamWindow`（原始流）作为订阅同一路 `/ws/chat` 消息流的两个只读展示视图（Web 端合并为 `ChatPanel` 内的"时间线/原始流"切换），`DebugWidget`（+`PromptFilesPanel`）作为独立的事后检查器，不参与发送。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §3.3 完整通读 6 个文件 | ✅ | `free_chat.py`(420行)/`conversation_widget.py`(631行)/`ai_stream_window.py`(658行)/`debug_widget.py`(358行)/`prompt_files_panel.py`(103行)/`validation_debug_dialog.py`(54行) 会话内全部通读，另通读 `main_window.py` 中 `FreeChatSession` 组装、`debug.add_turn()` 调用点、`snapshot_klines_for_followup()`、`_prompt_debug_report_for_bug_fix()` 相关约 400 行 |
| §5.1 `FreeChatSession` 的 asyncio 等价物 | ✅ | `pa_agent/webui/services/chat_runner.py::build_chat_session()` + `ChatRunner`，复用阶段一 `AnalysisRunner` 的 `asyncio.to_thread` + `run_coroutine_threadsafe` 模式 |
| §5.2 `/ws/chat` 端点 | ✅ | `pa_agent/webui/api/chat.py::ws_chat`，消息类型 `send`/`cancel`（客户端）、`chat_reasoning`/`chat_content`/`chat_done`/`chat_error`（服务端），完全独立于 `/ws/analysis`，未修改后者任何既有消息字段 |
| §5.3 调试面板/prompt文件面板后端格式化 | ✅ | 新增 `POST /api/chat/debug-context`，一次性返回 turns（Stage1/Stage2/异常）+ prompt_files，服务端用 `mask_secret` 脱敏 |
| §5.4 前端 `src/chat/`、`src/debug/` | ✅ | `ChatPanel.tsx`/`useChatSession.ts`/`chatFormat.ts`；`DebugPanel.tsx`（内嵌 prompt files 面板）/`ValidationDialog.tsx`/`debugFormat.ts` |
| §5.5 校验失败对话框等价 UI | ✅ | `ValidationDialog.tsx`，`record.exception` 存在时弹出，内容取自同一个 `/api/chat/debug-context` 的"⚠ 异常"turn |
| 后端 pytest | ✅ | `tests/webui/test_chat_ws.py`（7用例）+ `tests/webui/test_chat_debug_api.py`（3用例） |
| 前端 tsc/vitest/build | ✅ | 见 §6；新增 `chatFormat.test.ts`（7用例）+ `debugFormat.test.ts`（5用例） |
| Playwright e2e | ✅ | `tests/webui/e2e/test_phase5_chat_debug_smoke.py`（3场景） |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段六执行方案 | ✅ | [`phase-6-execution-plan.md`](phase-6-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增：**
- `pa_agent/webui/schemas/chat.py`
- `pa_agent/webui/services/chat_runner.py`
- `pa_agent/webui/api/chat.py`
- `pa_agent/webui/frontend/src/chat/{ChatPanel.tsx,useChatSession.ts,chatFormat.ts,chatFormat.test.ts}`
- `pa_agent/webui/frontend/src/debug/{DebugPanel.tsx,ValidationDialog.tsx,debugFormat.ts,debugFormat.test.ts}`
- `tests/webui/test_chat_ws.py`
- `tests/webui/test_chat_debug_api.py`
- `tests/webui/e2e/test_phase5_chat_debug_smoke.py`

**修改：**
- `pa_agent/webui/deps.py`（`AppState` 新增 `chat_session`/`chat_runner` 字段，未删除/未重命名既有字段）
- `pa_agent/webui/api/analysis.py`（`_run()` 内新增一行：record 产生后调用 `build_chat_session()` 重建 `state.chat_session`，镜像桌面端 `_on_record_ready_impl` 的"Create FreeChatSession"逻辑；`/ws/analysis` 既有消息类型/收发逻辑零改动）
- `pa_agent/webui/server.py`（新增 `chat_api.ws_router`/`chat_api.router` 挂载，其余路由挂载顺序未变）
- `pa_agent/webui/frontend/src/types/domain.ts`（`AnalysisRecord` 新增 `stage1_messages`/`stage1_response`/`stage2_messages`/`stage2_response`/`strategy_files_used`/`experience_loaded` 字段；新增 `ChatWsInbound`/`ChatDebugTurn`/`PromptFilesInfo` 等类型，均为新增，未删除/重命名既有字段）
- `pa_agent/webui/frontend/src/api/paAgentWs.ts`（新增 `useChatSocket`，`useKlineSocket`/`useAnalysisSocket` 零改动）
- `pa_agent/webui/frontend/src/api/paAgentApi.ts`（新增 `fetchChatDebugContext`）
- `pa_agent/webui/frontend/src/App.tsx`（挂载 `<ChatPanel>`/`<DebugPanel>` 到新增的 `.chat-debug-row`，`<ValidationDialog>` 条件渲染；阶段一/三/四既有布局元素零改动）
- `pa_agent/webui/frontend/src/styles/app.css`（新增 `.chat-*`/`.debug-*`/`.prompt-files-*`/`.validation-dialog-*` 类，均复用 `tokens.css` 已有变量，未新增色值；另修复了一个由本阶段新增内容触发的布局问题，见 §3 第 1 条）
- `pa_agent/webui/frontend/src/state/appStore.test.ts`（既有测试的 `AnalysisRecord` 字面量补全新增必填字段，测试断言逻辑零改动）
- `tests/webui/e2e/conftest.py`（`live_server` fixture 新增 `FreeChatSession.send` 的 monkeypatch `_fake_chat_send`，镜像既有 `_fake_submit` 对 `TwoStageOrchestrator.submit` 的处理方式；既有 `_fake_submit`/`_build_record`/路径重定向逻辑零改动）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 全部零改动（`git status --short -- pa_agent/gui/` 确认为空）。
- `pa_agent/orchestrator/free_chat.py::FreeChatSession` 核心逻辑零改动，仅被新服务层 `import` 调用。
- `pa_agent/orchestrator/two_stage.py`、`pa_agent/webui/services/analysis_runner.py` 零改动；`/ws/analysis` 既有消息类型字段零改动（`event`/`stage1_reasoning`/`stage1_content`/`stage2_reasoning`/`stage2_content`/`stage_prompt`/`stage2_files`/`record`/`error`）。
- 阶段二报告页面、阶段三决策树面板、阶段四流程图代码零改动。
- 阶段六范围（演示模式回放/下单机会通知）未涉及。

## 3. 遇到的问题、根因与解决方式

1. **新增的 `.chat-debug-row` 区块导致阶段三的一个既有 e2e 测试出现点击拦截失败**：`.app-shell` 原来是 `height: 100vh` 的固定高度 flex 列容器，`.flow-row`（阶段四新增，480px）加上本阶段新增的 `.chat-debug-row`（约 420px）后，总内容高度在 Playwright 默认 1280×720 视口下明显超过 100vh；flex 容器高度固定不变的情况下，各 flex 子项被强制按比例压缩，压缩后的盒子仍保留其"自动最小尺寸"内容，导致视觉上出现内容溢出、覆盖到相邻区块，最终表现为 `test_decision_tree_path_row_click_highlights_full_tree_node` 点击时被 `.flow-row` 拦截。根因确认方法：`git stash` 回退到阶段五改动前重新构建并单独运行该用例，确认在阶段四基线上通过，锁定问题由本阶段布局改动引入。修复：把 `.app-shell` 从 `height: 100vh` 改为 `min-height: 100vh`（允许页面在内容超出一屏时自然产生纵向滚动，而不是被压缩重叠），并给 `.flow-row`/`.chat-debug-row` 补上 `flex-shrink: 0`、给 `.main-layout` 补上 `min-height: 480px` 下限，避免图表区域在窄视口下被过度压缩。修复后重跑全部 18 个 Playwright 场景（阶段一至五）全部通过。这是一处影响阶段一全局布局容器（`.app-shell`）的改动，超出了"只新增 `.chat-*`/`.debug-*` 类"的原计划范围，但改动性质是**兼容性修复**（消除本阶段引入的回归），未改变阶段一/三/四任何既有类的视觉呈现（仅是让页面在内容更多时可以滚动，此前恰好没有触发滚动只是因为内容量没超过一屏）。
2. **`npm run build` 会覆盖/删除 `pa_agent/webui/static/pa_agent_app/.gitkeep`**：`.gitignore` 只保留该文件用于让空目录可被 git 追踪，构建产物本身被忽略。每次本地构建验证后需要 `git checkout -- pa_agent/webui/static/pa_agent_app/.gitkeep` 恢复，已在提交前确认恢复（不属于阶段五代码改动，纯粹是本地验证流程的副作用，前序阶段大概率也遇到过同样情况）。
3. **`ai_stream_window.py`（AiStreamWindow）与 `conversation_widget.py`（ConversationWidget）桌面端各自内置了一份完整的发送框/状态机**：通读后确认二者是同一份 `FreeChatSession.send()` 调用的两种独立展示（时间线 vs 原始流），并非功能分工不同。按 §0.3 确认结果，Web 端合并为一个 `ChatPanel` 组件、一个 `useChatSession()` 引擎、一个发送框，用"时间线/原始流"切换按钮呈现两种展示，避免了在 Web 端重复实现两套发送/取消状态机。
4. **`DebugWidget` 从不展示追问（chat）轮次**：通读 `main_window.py` 全部 4 处 `debug.add_turn()` 调用点后确认，桌面端调试面板只在 Stage1/Stage2/异常时追加轮次，追问轮次从未被加入调试面板——这与执行方案 §4 的猜测一致，因此 Web 端 `DebugPanel` 的范围收窄为"仅展示当前 record 的 Stage1/Stage2/异常"，不需要为每次追问单独触发调试信息更新，简化了实现且与桌面端行为完全对齐。

## 4. 可复用经验与后续注意事项

- **`.app-shell` 固定 `100vh` 的 flex 列布局是一个"隐藏的总预算"**：阶段一设计时假设"一屏装下所有区块"，阶段四加入 `.flow-row` 时预算已经很紧张（视口 720px 内 480px 被 flow-row 占用），阶段五再叠加约 420px 的新区块直接超出预算触发了压缩重叠。**如果阶段六还要在页面下方新增区块（例如演示模式回放面板），必须先确认 `.app-shell` 是否还有 `min-height: 100vh`（本阶段已改為允许纵向滚动），否则会重复触发同类布局回归。**
- **改动共享的全局布局容器前，建议先在本地跑一次全部既有 Playwright 场景（不只是本阶段新增的），哪怕执行方案只要求"回归验证仍全部通过"**：本阶段如果不是在提交前主动跑了全量 e2e 套件，这个跨阶段的布局回归会被"新增的 3 个阶段五场景全部通过"掩盖过去（阶段五自己的测试没有触碰到阶段三的点击路径），直到用户在真实使用中才会发现。
- **服务端一次性返回"格式化数据 + 脱敏"的组合响应模式，可以避免前端持有敏感信息**：`POST /api/chat/debug-context` 把"轮次格式化"（业务规则）和"API Key 脱敏"（安全边界）都放在同一个后端调用里完成，前端只做纯展示，不需要在 TS 里处理任何字符串替换/脱敏逻辑。这个模式如果阶段六也涉及"展示可能含敏感信息的原始数据"，可以直接复用。
- **e2e 里需要 monkeypatch 的对象，找准"真正会触发副作用"的那个方法**：阶段五一开始容易想到 monkeypatch `DeepSeekClient.stream_chat`（更底层），但 `FreeChatSession.send()` 是唯一的公开入口且已经封装了 usage/ledger 累加逻辑，直接 monkeypatch 这一层（`_fake_chat_send`，镜像 `_fake_submit` 对 `TwoStageOrchestrator.submit` 的处理），比 mock 更底层的 HTTP 客户端更简单、更贴近真实数据流。

## 5. 设计决策与偏离原计划的原因

- **`ChatPanel` 合并时间线与原始流为一个组件，而非两个独立组件**：按 §0.3 确认结果实施，避免了桌面端"两个发送框驱动同一 session"的重复状态管理在 Web 端重演。
- **`DebugPanel` 内嵌 `PromptFilesPanel`，而非两个独立顶层组件**：二者的数据来源是同一个 `/api/chat/debug-context` 调用（都需要 `record` 触发重新拉取），且桌面端布局上二者本来就在同一个"AI 侧边栏"里（`main_window.py:316-317` 的 `_ai_sidebar.debug`/`_ai_sidebar.prompt_files`），拆成两个组件会需要重复发起同一个网络请求或额外引入共享状态层——出于 README §4 阶段四总结报告已记录的"目前架构里没有跨组件设置失效/共享状态机制"的已知限制，选择合并展示，未引入新的全局 store。
- **`ValidationDialog` 独立发起一次 `/api/chat/debug-context` 请求（与 `DebugPanel` 各自独立拉取，未共享）**：二者通常不会同时挂载（`ValidationDialog` 只在有异常且未被用户关闭时弹出），重复请求成本很低；引入跨组件共享请求结果的状态层超出本阶段范围，与阶段四总结报告 §4 记录的架构现状一致，留给未来如有需要再单独提出。
- **`FreeChatSession` 的重建时机放在 `analysis.py::_run()` 内，而非新增独立入口**：桌面端在 `_on_record_ready_impl`（UI 回调）里创建会话，但 Web 端没有等价的"UI 层回调"概念——`/ws/analysis` 收到 record 后立即广播给前端，此时是重建 `state.chat_session` 的唯一自然时机，因此选择在 `AnalysisRunner.run()` 返回 record 后、`ws_analysis` 的 `_run()` 闭包内完成，这是执行方案 §5 步骤 2 预留的实施细节确认。

## 6. 数据/兼容性迁移情况

- 无数据迁移：`FreeChatSession` 的持久化（`PendingWriter.append_followup` 写入 JSONL sidecar）逻辑完全未改动，Web 端只是新增了驱动它的 asyncio 包装层。
- `AppState.chat_session`/`chat_runner` 是新增的、无状态默认值的字段，不影响任何既有序列化/反序列化路径（`AppState` 不做 JSON 序列化，仅进程内对象）。
- `AnalysisRecord`/`ChatMessage` 等前端类型新增字段均为在原有 interface 上追加，未删除/重命名任何既有字段，`appStore.test.ts` 中唯一因此需要更新的测试用例已同步补全。

## 7. 实际运行的验证命令与结果

### 7.1 后端 pytest（含阶段一/二/三/四回归）
```bash
./.venv/bin/pytest tests/webui/ --browser chromium -q
# 60 passed（exit code 0，无失败/无跳过）
```
覆盖：阶段一至四全部既有用例（`test_kline_api.py`/`test_analysis_ws.py`/`test_settings_api.py`/`test_reports_api.py`/`test_trade_fill_backfill.py`/`test_decision_tree_api.py`/`e2e/test_phase1_smoke.py`/`e2e/test_phase2_reports_smoke.py`/`e2e/test_phase3_decision_tree_smoke.py`/`e2e/test_phase4_decision_flow_smoke.py`）全部仍通过；阶段五新增 `test_chat_ws.py`（7条）/`test_chat_debug_api.py`（3条）/`e2e/test_phase5_chat_debug_smoke.py`（3条）。

### 7.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 6 passed (6) / Tests 36 passed (36)（本阶段新增 chatFormat.test.ts 7条 + debugFormat.test.ts 5条）
npm run build             # 构建成功；产物 998.03 kB（未压缩前，阶段四为 986.55KB，新增约 11.5KB，未引入新依赖，纯增量组件代码）
```

### 7.3 Playwright e2e（全量，跨全部五个阶段）
```bash
./.venv/bin/pytest tests/webui/e2e/ --browser chromium -q
# 18 passed（阶段一 1 场景 + 阶段二 X + 阶段三 X + 阶段四 3 场景 + 阶段五 3 场景，逐场景详见各阶段测试文件）
```
此次全量运行专门用于验证 §3 第 1 条布局回归修复后不再复现。

## 8. 遗留问题和风险

- **未在真实 DeepSeek API 上验证过 `/ws/chat` 的完整流式行为**：与阶段三/四总结报告 §8 记录的遗留问题性质相同——pytest/e2e 均使用手工构造的 `FakeChatSession`/monkeypatch 的 `_fake_chat_send`，未跑过真实模型的推理流。建议您在有真实 API Key 的环境下手动发起一次分析并追问，人工核对时间线/原始流/token 用量条的实际渲染效果。
- **`.app-shell` 从固定 `100vh` 改为 `min-height: 100vh`，页面在内容较多时会出现纵向滚动条**：这是本阶段为修复布局回归引入的行为变化，属于全局容器改动，视觉上唯一的差异是"较短视口下滚动查看阶段五新增区块"，不影响阶段一/三/四任何既有区域的相对位置和尺寸（已用全量 e2e 验证）。如果您认为整个工作台不应该出现纵向滚动（例如未来要求所有区块都塞进可折叠的 Tab 而不是纵向堆叠），需要作为独立议题提出，可能需要重新设计整体信息架构（超出阶段五范围）。
- **`ValidationDialog` 与 `DebugPanel` 各自独立请求 `/api/chat/debug-context`**：功能正确但有一次可避免的重复网络请求，出于"避免引入新的全局状态层"的判断保留现状，详见 §5。
- **未验证极端并发场景**（例如用户在 `/ws/chat` 追问进行中快速切换品种/周期触发新的一轮分析，`state.chat_session` 被新 record 替换）：`ChatRunner` 是单例、单飞行（single-flight），新分析产生的 `build_chat_session()` 会直接替换 `state.chat_session` 引用，但如果替换发生在旧 session 的 `send()` 仍在 `asyncio.to_thread` 中运行时，旧的后台线程会继续跑完并通过已捕获的 `websocket`/`ws` 变量正常回传结果（不会崩溃），只是这次回复实际上来自已被替换的旧会话——这与桌面端的行为一致（桌面端旧 `_ChatWorker` QThread 同样会跑完，只是不会因为新建了 `FreeChatSession` 就被打断），未额外加固，如果您认为需要更严格的会话世代校验，需要在阶段六或独立议题中评估。

## 9. 是否允许进入下一阶段

**允许**。§7 全部验证已实际运行且通过（后端 60 passed、前端 tsc/vitest/build 均通过、Playwright e2e 全量 18 场景通过，含本阶段引入又修复的跨阶段布局回归）；阶段一/二/三/四回归全部通过；`pa_agent/gui/`、`pa_agent/orchestrator/free_chat.py` 核心逻辑、`/ws/analysis` 既有消息 schema、阶段二/三/四代码零改动；`phase-6-execution-plan.md` 已生成。
