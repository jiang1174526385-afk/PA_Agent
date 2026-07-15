# 阶段五执行方案：自由对话 + AI 调试面板

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-4-completion-report.md`](phase-4-completion-report.md)（状态 `complete`）
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段六内容（演示模式回放 + 下单机会通知）及之后各阶段。

## 0. 需要您决策的问题（实施 session 开始前应先确认，不得自行假设）

1. **`WS /ws/chat` 是否复用 `/ws/analysis` 的连接/消息模式，还是独立一条 WebSocket？** 总纲 §5 阶段五条目建议"均可复用阶段一 `/ws/analysis` 已建立的消息流模式"，但 `FreeChatSession`（`pa_agent/orchestrator/free_chat.py`）是锚定在一个已完成的 `AnalysisRecord` 上的独立会话对象（`base_record`/`kline_snapshot_fn`/`SessionTokenLedger` 各自持有状态），与 `/ws/analysis` 驱动的 `AnalysisRunner`（阶段一）在生命周期上不同：分析是"一次提交一次结果"，自由对话是"同一 record 上下文里的多轮追问"。是否需要为聊天单独开一条 WS（`/ws/chat`，每次连接绑定一个 record_id）、还是在既有 `/ws/analysis` 连接上复用消息类型区分（`type: "chat_send"` vs `type: "submit"`），需要您确认——这决定后端 `AppContext`/连接管理的改动范围。
2. **调试面板（`DebugWidget`）的敏感信息处理边界**：桌面端 `DebugWidget` 会展示原始 `raw_response`（含 HTTP headers/body/`request_id`）并用 `mask_secret` 遮盖 API Key。总纲 §7 要求"密钥字段任何 API 响应都不得明文回显"——`raw_response` 里除了 API Key，是否还可能包含其它需要脱敏的内容（例如请求头里的其它认证信息、DeepSeek 返回的 `request_id` 是否可回显）？这需要在实施前明确"调试面板 Web 版可以完整展示到什么颗粒度"，而不是照搬桌面端全量转发。
3. **`AiStreamWindow`（657 行，阶段五清单里体量最大的桌面组件）的定位是否等同"原始 token 流控制台"**：总纲 §5 阶段五条目只提到"原始 token 流控制台"一句话带过，但 `ai_stream_window.py` 行数与 `conversation_widget.py`（630 行）相当，需要在完整读完后确认它与 `DebugWidget`/`ConversationWidget` 的功能是否有重叠（例如是否也展示 turn 列表/时间线），以避免 Web 端重复实现三套相似的"展示 AI 交互记录"组件。是否可以合并为一个 Web 组件（例如 `DebugWidget` 面板内嵌一个"原始流"子视图），还是必须保持三个独立组件与桌面端一一对应，需要您确认设计取舍。

## 1. 阶段目标

把以下 5 个桌面组件迁移为 Web 组件，视觉沿用**阶段一暗色主题**：

- `pa_agent/gui/conversation_widget.py`（630 行）——自由对话时间线 UI，基于 `pa_agent/orchestrator/free_chat.py::FreeChatSession`（420 行）
- `pa_agent/gui/ai_stream_window.py`（657 行）——原始 token 流展示窗口
- `pa_agent/gui/debug_widget.py`（357 行）——AI 调试面板（system/user prompt、原始响应、校验信息，4 栏只读文本）
- `pa_agent/gui/prompt_files_panel.py`（102 行）——本次分析注入的 .txt 文件列表（阶段一/阶段二两栏 + 经验库计数）
- `pa_agent/gui/validation_debug_dialog.py`（53 行）——校验失败时的调试对话框（摘要 + 可复制正文）

## 2. 非目标

- 不实现演示模式回放/下单机会通知（阶段六）。
- 不改动阶段二报告页面、阶段三决策树面板、阶段四流程图的任何代码。
- 不改动 `pa_agent/orchestrator/two_stage.py`、`pa_agent/webui/services/analysis_runner.py`、`/ws/analysis` 既有消息 schema（除非 §0.1 决策要求复用同一连接，此时改动仅限于新增消息类型，不得删除/重命名既有消息类型字段）。
- 不改动 `pa_agent/orchestrator/free_chat.py::FreeChatSession` 的核心逻辑——只包装成 asyncio/WS 等价物（参照总纲 §1 对 `RefreshLoop`/`_AnalysisWorker` 的处理方式）。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-4-completion-report.md`。
2. `git status --short`，确认阶段四的改动已按用户要求处理，不得回滚。
3. **完整通读以下 6 个文件**（本执行方案只读了每个文件的开头片段，未覆盖完整交互细节）：
   - `pa_agent/orchestrator/free_chat.py`（420 行，`FreeChatSession` 的完整生命周期：`send()`/token 账本/`kline_snapshot_fn` 注入时机）
   - `pa_agent/gui/conversation_widget.py`（630 行，时间线摘要/详情懒加载模型 `_TurnRecord`、`QThread` 包装 `FreeChatSession.send()` 的方式）
   - `pa_agent/gui/ai_stream_window.py`（657 行，未读——见 §0.3）
   - `pa_agent/gui/debug_widget.py`（357 行，turn 数据模型、`mask_secret` 用法、JSON 导出）
   - `pa_agent/gui/prompt_files_panel.py`（102 行，体量小，已基本读完，实施时仍需二次确认无遗漏）
   - `pa_agent/gui/validation_debug_dialog.py`（53 行，已读完）
4. 确认 §0 三个决策问题已经和您对齐。
5. 复用阶段三/四已确认的分工原则：格式化/业务规则留在 Python（`pa_agent/orchestrator/free_chat.py` 相关的 turn 格式化、`mask_secret` 脱敏逻辑），几何/纯展示布局在前端实现，不在 TS 里重新实现业务规则。

## 4. 当前代码事实摘要（不完整，实施时必须重新通读全文核实）

- `FreeChatSession.__init__` 依赖 `DeepSeekClient`/`PromptAssembler`/`PendingWriter`/`SessionTokenLedger`/`Settings`/`kline_snapshot_fn` 六个协作对象，均来自 `pa_agent/gui/main_window.py` 桌面端的组装逻辑——Web 端需要在 `pa_agent/webui/services/`（参照阶段一 `AnalysisRunner`/`RefreshBroadcaster` 的既有组装方式）新增一个等价的组装点，实施时必须先读 `main_window.py` 里 `FreeChatSession` 是如何被实例化、何时创建/销毁（每次新分析后新建，还是复用）。
- `conversation_widget.py` 的 `_TurnRecord` 数据模型区分 `kind: "stage" | "user" | "chat"` 三种时间线条目类型，摘要（`timeline_summary()`）与详情懒加载分离——这个"列表摘要 + 点击加载详情"的 UI 模式与阶段三 `DecisionTreePanel` 的路径表格/完整树两级展示、阶段四流程图的节点 hover-tooltip 摘要模式是同一思路的延续，Web 端可以复用类似的组件设计习惯（受控展开、`title` 属性做摘要提示）。
- `debug_widget.py` 的 turn 数据模型是纯 dict（`label`/`system_prompt`/`user_prompt`/`raw_response`/`validation_info`），本身已经与 PyQt 无关，是否可以整体作为 Web 端的响应 DTO 直接复用字段名，需要在完整读完后确认 `raw_response` 的具体结构（`AIReply.raw`，未在本文件读到定义处）。
- `mask_secret`（`pa_agent/util/mask_secret.py`，阶段一已在 `ProviderRead`/`FeishuRead` 等 settings DTO 中使用过）是项目既有的脱敏工具，`DebugWidget` 用它遮盖 `api_key`——Web 端调试面板端点必须复用同一个函数，不得自己实现一份字符串脱敏逻辑。
- `validation_debug_dialog.py` 是一个通用的"标题+摘要+可复制正文"模态框，被谁调用（大概率是 `main_window.py` 里校验失败/异常时触发）需要在实施时搜索调用点确认触发时机，才能决定 Web 端应该在哪个事件（`/ws/analysis` 的 `error` 消息？新增消息类型？）上弹出等价 UI。

## 5. 实施步骤（骨架，实施 session 必须先完整读完 §3 列出的文件再据实调整/展开）

1. 完整通读 `free_chat.py`/`conversation_widget.py`/`ai_stream_window.py`/`debug_widget.py`，梳理：`FreeChatSession` 的组装/生命周期、`_TurnRecord` 完整字段、`ai_stream_window.py` 与其它两个组件的功能边界（§0.3）。
2. 根据 §0.1 的决策，设计聊天的 WS 端点（新端点或复用 `/ws/analysis`）；设计 `POST`（如需要，例如"开始一个新的自由对话会话"这类一次性操作可能不适合走 WS）与 WS 消息的划分。
3. 后端：新增 `pa_agent/webui/services/`（自由对话会话管理，asyncio 等价物）+ `pa_agent/webui/api/`（如需 REST 端点，例如获取当前 turn 列表/调试信息）+ `pa_agent/webui/schemas/`（新增 DTO，复用 `mask_secret`）。
4. 前端：`src/chat/`（自由对话时间线 + 输入框）、`src/debug/`（调试面板 + prompt files 面板 + 校验对话框），均沿用暗色主题 `tokens.css`。
5. 校验失败对话框的等价 UI（弹窗还是内联面板，取决于 §0.1/§4 实施时对触发点的确认结果）。

## 6. 兼容策略与回滚点

- 新增代码位于 `pa_agent/webui/frontend/src/chat/`、`pa_agent/webui/frontend/src/debug/`；后端新增文件放在 `pa_agent/webui/services/`、`pa_agent/webui/api/`、`pa_agent/webui/schemas/` 对应位置，与阶段一/三/四的目录习惯一致。
- `pa_agent/gui/conversation_widget.py`、`ai_stream_window.py`、`debug_widget.py`、`prompt_files_panel.py`、`validation_debug_dialog.py`、`pa_agent/orchestrator/free_chat.py` 均不改动核心逻辑。
- 若 §0.1 决定复用 `/ws/analysis`，改动限定为新增消息类型（不删除/不重命名阶段一已有消息类型字段），保证阶段一 K线/分析流程不受影响。

## 7. 测试与验证命令

- 后端 pytest：`FreeChatSession` 的 asyncio 包装层、新增 API/WS 端点的用例。
- 前端：`tsc --noEmit`/`npm run build`/`npx vitest run`（新增聊天时间线/调试面板的纯展示逻辑单测，参照阶段四 `layout.test.ts` 的模式）。
- Playwright e2e：`tests/webui/e2e/test_phase5_chat_debug_smoke.py`——提交一次分析后进入自由对话发一条消息并收到回复、调试面板展示至少一个 turn 且 API Key 已脱敏、prompt 文件列表非空。

## 8. 验收标准

- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 阶段一/二/三/四回归验证仍全部通过。
- 已生成 `phase-5-completion-report.md` 和 `phase-6-execution-plan.md`。

## 9. 停止条件

- §0 三个决策问题未获得您的确认前，不得开始实施。
- 通读 §3 列出的 6 个文件后，如果发现 `ai_stream_window.py` 与其它两个组件的功能重叠程度、或 `FreeChatSession` 的组装方式复杂度远超本文件 §4 的摘要判断，需要重新评估工作量并向您报告，不得为了赶进度简化到明显偏离桌面端行为的程度而不说明。
- 若调试面板的敏感信息脱敏边界（§0.2）在实施中发现比预想更复杂（例如 `raw_response` 包含无法安全展示的字段），必须暂停并向您确认，不得自行决定展示范围。
