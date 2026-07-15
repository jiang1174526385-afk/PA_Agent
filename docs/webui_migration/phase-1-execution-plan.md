# 阶段一执行方案：基础设施 + MVP 核心闭环

> 所属总纲：[`README.md`](README.md)
> 阶段状态：`ready`
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段二内容（交易记录分析报告页面，参照 `pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg`）及之后各阶段。

## 1. 阶段目标

在不改动 `pa_agent/orchestrator`/`pa_agent/data`/`pa_agent/config`/`pa_agent/records`/`pa_agent/notify` 等核心业务逻辑、且不破坏 `pa_agent/gui/` 现有桌面应用可运行性的前提下，搭建 FastAPI + React/TypeScript 的 Web 前端骨架，跑通以下核心闭环：

1. 数据源（MT5/TradingView/OKX）切换 → symbol/timeframe 联动 → K线图实时展示（含 EMA20/ATR14 叠加）；
2. 提交分析/增量分析（WebSocket 流式）→ DecisionPanel（交易决策/置信度/胜率/理由）+ FutureTrendPanel（下一根K线/下一周期预测）展示结果，支持分析中途取消；
3. 设置页：AI 模型、通用设置、飞书、PushPlus 四个分区的读取与保存（密钥字段脱敏，不做实际通知触发）。

## 2. 非目标

本阶段明确不做，发现相关问题只记录、不顺手实现：

- 不实现"交易记录分析报告"页面（新增页面，参照 `pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg` 的浅色卡片仪表盘设计，数据来自 `pa_agent/records/trade_logger.py` 的 CSV，属于阶段二，与本阶段的暗色主题工作台完全独立，不要因为看到设计图就顺手在本阶段搭建）；
- 不实现 DecisionTreePanel（决策树回放，现为阶段三）；
- 不实现 DecisionFlowViz（动画流程图可视化）；
- 不实现 ConversationWidget（自由对话）；
- 不实现 AIStreamPanel/DebugWidget/PromptFilesPanel/ValidationDebugDialog（调试类面板）；
- 不实现演示模式回放；
- 不实现下单机会弹窗，也不接入飞书/PushPlus 的实际通知发送逻辑（设置页只做配置项 CRUD）；
- 不删除、不重构 `pa_agent/gui/` 任何代码；
- 不改动 `pa_agent/orchestrator/two_stage.py`、`pa_agent/data/base.py` 等核心契约（除非发现阻塞性 bug，须先记录并征求用户同意再改）；
- 不引入用户鉴权/多用户支持（`start_webui.py` 默认绑定 `127.0.0.1`，单用户本地使用）。

## 3. 前置条件

开始本 Session 时必须：

1. 读取 [`README.md`](README.md) 和本文件；
2. 检查 `git status --short`，识别并保留用户已有修改（不清理、不回滚无关变更）；
3. 确认 `.venv` 存在且可用（若不存在，按 `CONTRIBUTING.md` 的方式创建：`python -m venv .venv`）；
4. 通读 `pa_agent/gui/main_window.py` 中 `_AnalysisWorker` 类定义及其信号连接部分（作为 Web 端消息设计的行为参照）；
5. 通读 `pa_agent/data/refresh_loop.py::RefreshLoop` 完整实现（作为 `RefreshBroadcaster` 的行为参照，包括指数退避常数）；
6. 通读 `pa_agent/app_context.py::AppContext.bootstrap`（作为 Web 端 lifespan 复用的基础）；
7. 抽查 `tradingAgents/webui/server.py` 和 `tradingAgents/webui/frontend/src/state/terminalStore.ts`，确认本阶段沿用的架构模式仍然成立（若参考项目结构已发生较大变化，需在总结报告中记录差异）。

## 4. 当前代码事实（来自前期调研，实施时仍需按需核实）

- `pa_agent/data/base.py::DataSource`：`connect()`/`disconnect()`/`list_symbols()`/`supported_timeframes()`/`subscribe(symbol, timeframe)`/`unsubscribe()`/`latest_snapshot(n) -> list[KlineBar]`，同步、无 Qt 依赖。
- `pa_agent/data/factory.py::create_data_source(kind)`：`kind` 取值含 `mt5`/`tradingview`/`okx`（用户可见）等。
- `pa_agent/data/snapshot.py`：纯函数，`take_snapshot_from_bars`/`compute_indicators`/`build_display_frame`/`build_live_frame`/`build_analysis_frame`，用于把裸 bar 列表转成 `KlineFrame`。
- `pa_agent/orchestrator/two_stage.py::TwoStageOrchestrator.submit(frame, cancel_token, on_event, on_stage1_reasoning=, on_stage1_content=, on_stage2_reasoning=, on_stage2_content=, on_stage_prompt=, on_stage2_files=, previous_record=, incremental_new_bar_count=) -> AnalysisRecord`：同步阻塞，流式回调为普通可调用对象，同步触发。
- `pa_agent/util/threading.py::CancelToken`：`threading.Event` 包装，`submit()` 内部已有取消检查点，无需改动即可复用。
- `pa_agent/config/settings.py`：`AIProviderSettings`/`GeneralSettings`/`PromptSettings`/`ValidationSettings`/`FeishuSettings`/`PushPlusSettings`/`TushareSettings`，`load_settings`/`save_settings` 读写 `config/settings.json`；`api_key_encrypted` 字段为已废弃/迁移字段，读取后应从 API 响应中剔除。
- `pa_agent/util/mask_secret.py::mask_secret(s)`：现成的密钥脱敏函数，直接复用。
- `pa_agent/gui/theme/tokens.py`：真实取值（非估算）——`BG="#0a0e14"`、`SURFACE_1="#161b22"`、`FG="#e6edf3"`、`FG_2="#8b949e"`、`ACCENT="#2dd4bf"`、`SUCCESS="#22c55e"`、`DANGER="#ef4444"`、`WARNING="#f59e0b"`、`CHART_UP="#22c55e"`、`CHART_DOWN="#ef4444"`，以及 PILL_*/FONT_*/RADIUS/SPACING 等完整 token 集合，需要在本阶段实施时逐项读取该文件并 1:1 转成 CSS 变量。
- `pa_agent/app_context.py::AppContext.bootstrap()`：Qt 无关，完整wiring settings/data_source/AI client/orchestrator 所需的全部协作对象，可直接在 FastAPI `lifespan` 中调用一次。

## 5. 实施步骤

### 5.1 后端骨架

1. 新建 `pa_agent/webui/__init__.py`、`pa_agent/webui/server.py`：
   - `lifespan()` 异步上下文管理器：启动时 `app.state.ctx = AppContext.bootstrap()`，初始化 broadcaster 注册表；关闭时取消所有活跃 `RefreshBroadcaster` 任务并 `data_source.disconnect()`。
   - `app = FastAPI(title="PA Agent", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)`。
   - 开发模式下允许 `http://localhost:5173` 的 CORS（生产构建同源，不需要）。
   - 挂载各 `api/*.py` 路由，前缀 `/api`；挂载 `pa_agent/webui/static/pa_agent_app/` 作为 SPA 静态资源，非 `/api`、非 `/ws` 的 GET 请求 fallback 到 `index.html`（`index.html` 响应加 no-cache 头）。
2. 新建 `pa_agent/webui/deps.py`：
   - 提供 `get_ctx(request) -> AppContext` 依赖函数；
   - 维护 `dict[tuple[str, str, str], RefreshBroadcaster]` 单例注册表 + `asyncio.Lock`；
   - 维护当前是否有分析任务在跑的单飞状态（`AnalysisRunner` 是否占用中）。

### 5.2 K线数据流

3. `pa_agent/webui/services/refresh_broadcaster.py::RefreshBroadcaster`：
   - 构造参数：`data_source: DataSource`、`n_bars`、`interval_ms`；
   - `async def _loop(self)`：`bars = await asyncio.to_thread(self._source.latest_snapshot, n)`，成功时用 `pa_agent/data/snapshot.py` 的纯函数构建 `KlineFrame` 并广播 `{"type":"frame",...}`；捕获 `DataSourceTransientError` 时按 `refresh_loop.py` 原有的指数退避常数 `await asyncio.sleep(backoff)` 并广播 `{"type":"status",...}`；
   - `add_subscriber(ws)`/`remove_subscriber(ws)`，最后一个订阅者移除时 `task.cancel()`。
4. `pa_agent/webui/api/kline.py`：
   - `GET /api/data-sources` → 静态列表；
   - `GET /api/data-sources/{kind}/symbols`、`GET /api/data-sources/{kind}/timeframes`（非当前活跃 kind 时临时 `create_data_source(kind)` + `connect()` + 查询 + `disconnect()`）；
   - `GET /api/kline/snapshot?source=&symbol=&timeframe=&n=`（一次性快照，`asyncio.to_thread` 调用）；
   - `WS /ws/kline`：接收 `{"type":"subscribe","source":...,"symbol":...,"timeframe":...,"n_bars":...}`，切换时按 §5.2 设计取消旧订阅、`data_source.subscribe(...)`、注册新 broadcaster；每帧消息带 `epoch` 字段（每次 `subscribe` 自增），客户端据此丢弃过期帧。

### 5.3 AI 分析流

5. `pa_agent/webui/services/analysis_runner.py::AnalysisRunner`：
   - 单进程单飞：新提交到达时若已有任务在跑，返回 `{"type":"error","message":"分析进行中"}` 并拒绝；
   - `submit()` 前 `loop = asyncio.get_running_loop()`，通过 `asyncio.to_thread(orchestrator.submit, frame, cancel_token, on_event, on_stage1_reasoning=cb, ...)` 调度；
   - 各回调内 `asyncio.run_coroutine_threadsafe(websocket.send_json({...}), loop)`；
   - 消息类型：`event`（`OrchestratorEvent` 名称）、`stage1_reasoning`/`stage1_content`/`stage2_reasoning`/`stage2_content`（`{"chunk":...}`）、`stage_prompt`（`{"stage":...,"system":...,"user":...}`）、`stage2_files`（`{"files":[...]}`）、`status`、`retry`、`record`（最终 `AnalysisRecord.model_dump()`）、`error`；
   - 取消：客户端发 `{"type":"cancel"}` → `cancel_token.set()`；`WebSocketDisconnect` 时同样 `cancel_token.set()`，防止后台线程空跑；
   - 异常兜底：`asyncio.to_thread(...)` 抛出未预期异常时捕获并发送 `{"type":"error",...}`，避免后台任务异常无声丢失。
6. `pa_agent/webui/api/analysis.py`：`WS /ws/analysis`，接收 `{"type":"submit","mode":"full"|"incremental","n_bars":...,"incremental_new_bar_count":...}`（服务端取当前活跃 `RefreshBroadcaster` 持有的最新 `KlineFrame`）与 `{"type":"cancel"}`。

### 5.4 设置 API

7. `pa_agent/webui/schemas/settings.py`：每个 section 一对 DTO（Read 用真实值+脱敏，Write 用 `Optional[str]=None` 语义的密钥字段）。
8. `pa_agent/webui/api/settings.py`：
   - `GET /api/settings/{section}`：`load_settings()` 取值，密钥字段用 `mask_secret()` 脱敏并附 `xxx_set: bool`，剔除 `api_key_encrypted`；
   - `PUT /api/settings/{section}`：合并非密钥字段 + 密钥字段（`None`=不变，`""`=清空，非空=设置新值）后 `save_settings()`，响应仍为脱敏后的 GET 形状。
9. `pa_agent/webui/api/models.py`：`GET /api/ai/models`，若 `pa_agent/ai/client_factory.py` 无现成 list-models 接口，用精选常量列表 + 前端自由文本输入框兜底（实施时先确认该接口是否存在，若不确定需在总结报告中记录判断依据）。

### 5.5 前端骨架

10. `pa_agent/webui/frontend/`：`package.json`（`react@^19`、`react-dom@^19`、`lightweight-charts@^5.2.0`、`marked`、`clsx`；devDeps `typescript@^5.7`、`vite@^6`、`@vitejs/plugin-react`、`vitest`、`@types/react`、`@types/react-dom`）、`vite.config.ts`（`build.outDir` 指向 `../static/pa_agent_app`，dev 模式 proxy `/api`、`/ws` 到 `127.0.0.1:8765`）、`tsconfig.json`、`index.html`。
11. `src/state/appStore.tsx`：`React.createContext` + `useReducer`，状态含当前 source/symbol/timeframe、当前 `KlineFrame`、最新 `AnalysisRecord`、分析进行中标志+流式缓冲、settings 缓存、两个 WS 的连接状态。
12. `src/api/client.ts`/`paAgentApi.ts`/`paAgentWs.ts`：REST 封装、类型化调用、`useKlineSocket`/`useAnalysisSocket`（含重连退避与 `epoch` 过滤逻辑）。
13. `src/chart/ChartView.tsx` + `useLightweightChart.ts`：K线蜡烛图 + EMA20/ATR14 折线；`decisionOverlay.ts`：分析结果到来时增删 entry/SL/TP 价格线（参考 `pa_agent/gui/chart_decision_overlay.py` 字段含义，按需查阅，不做逐行照搬）。
14. `src/toolbar/Toolbar.tsx`：数据源/symbol/timeframe 选择、获取数据/提交分析/增量分析按钮（分析进行中禁用，与桌面端一致）、演示模式按钮渲染为 disabled + "阶段五开放" 提示。
15. `src/decision/DecisionPanel.tsx`、`FutureTrendPanel.tsx`：渲染 `AnalysisRecord` 对应字段，理由文本走 markdown 渲染。
16. `src/settings/SettingsModal.tsx` + 四个 Tab 组件：密钥字段用密码输入框，placeholder 显示脱敏值，需要显式"修改"操作才能清空重填，不回显真实密钥。
17. `src/styles/tokens.css`：从 `pa_agent/gui/theme/tokens.py` 逐项手工转换为 CSS 自定义属性（含 pill/chart 系列色值）。

### 5.6 入口与工具链

18. `pyproject.toml` 新增 `[project.optional-dependencies].webui = ["fastapi>=0.115", "uvicorn[standard]>=0.30", "websockets>=13"]`；`dev` 组新增 `pytest-asyncio>=0.24`、`playwright>=1.47`、`pytest-playwright>=0.5`。
19. 根目录新建 `start_webui.py`（复用 `run.py` 的 `sys.path`/`cwd` 处理，`argparse` 支持 `--host`（默认 `127.0.0.1`）/`--port`（默认 `8765`）/`--reload`，`uvicorn.run("pa_agent.webui.server:app", ...)`）。
20. `Makefile` 新增 `run-webui`/`dev-webui-frontend`/`build-webui-frontend` targets。

## 6. 兼容策略与回滚点

- 所有新增代码位于 `pa_agent/webui/`、`pa_agent/webui/frontend/`、根目录 `start_webui.py`，与现有 `pa_agent/gui/`、`run.py` 完全隔离，互不影响；回滚只需删除这些新增路径 + 还原 `pyproject.toml`/`Makefile` 的新增段落。
- 若实施过程中发现必须改动核心模块（如 `DataSource`/`TwoStageOrchestrator` 接口不足以支撑 Web 场景），必须先停下来在总结报告中记录具体缺口和影响范围，并征求用户同意后再改，不得默默改动。

## 7. 测试与验证命令

### 7.1 依赖准备

```bash
cd /home/jack/quant_trading_system_v2/PA_Agent
source .venv/bin/activate
pip install -e ".[dev,webui]"
playwright install chromium
```

若安装过程中出现依赖冲突（版本不兼容等），暂停并向用户报告冲突详情，不自行降级或强制安装。

### 7.2 后端测试

```bash
./.venv/bin/pytest -q tests/webui/
```

新增 `tests/webui/test_data_sources_api.py`、`test_kline_api.py`、`test_settings_api.py`、`test_analysis_ws.py`：

- `test_settings_api.py`：断言 `GET /api/settings/provider` 不含明文 `api_key`，只含脱敏值 + `api_key_set`；断言 `api_key_encrypted` 不出现在响应中；断言 `PUT` 传 `api_key: null` 不改变已存储的值（通过 `load_settings` 复核）。
- `test_analysis_ws.py`：注入假的 `TwoStageOrchestrator`（同步 sleep + 回调），断言 WS 消息顺序符合预期；断言发送 `{"type":"cancel"}` 后 `cancel_token.is_set()` 为真，且收到带 `Cancelled` 标记的记录。
- `test_kline_api.py`：注入假 `DataSource`（实现 `pa_agent/data/base.py::DataSource`），用短 `interval_ms` 验证 `RefreshBroadcaster` 按预期节奏广播帧（`asyncio` 测试内 `sleep`，不打真实网络）。

### 7.3 前端静态检查

```bash
cd pa_agent/webui/frontend
npx tsc --noEmit
npm run build
npx vitest run
```

### 7.4 浏览器端到端测试（Playwright）

新增 `tests/webui/e2e/test_phase1_smoke.py`（或等价目录），用 `pytest-playwright` 驱动真实 Chromium，针对 `start_webui.py` 启动的实例 + 已 `npm run build` 的前端跑通以下场景（均为自动化断言，不是人工目测）：

1. 打开页面，断言暗色主题关键 CSS 变量/背景色已生效、无 JS console error。
2. 依次切换 MT5/TradingView/OKX 数据源，断言 symbol/timeframe 下拉框内容随之更新。
3. 点击"获取数据"，断言图表容器渲染出蜡烛图元素且请求了 `/api/kline/snapshot`；保持页面打开数秒，断言通过 `/ws/kline` 收到至少一条新 `frame` 消息。
4. 点击"提交分析"，断言 DecisionPanel/FutureTrendPanel 从加载态最终变为含结果字段的状态，并断言对应 `records/pending/*.json` 文件已生成。
5. 触发"增量分析"，断言请求携带了预期的 `previous_record`/`incremental_new_bar_count` 参数。
6. 分析进行中点击取消，断言 UI 在合理时间内回到 idle 态。
7. 打开设置弹窗，断言密钥字段显示为脱敏文本；修改一个非密钥字段并保存，刷新页面后断言该值仍生效，并核对 `config/settings.json` 落盘内容。
8. 分析进行中关闭页面/断开连接，断言无孤儿线程继续运行（可通过临时日志标记验证）。

运行：

```bash
./.venv/bin/pytest -q tests/webui/e2e/ --browser chromium
```

遇到 Playwright 环境问题（缺系统依赖、`playwright install` 失败等）按 §7.1 原则暂停提问，不得退化为跳过测试掩盖问题。

## 8. 验收标准

- §7 全部四类验证（pytest、tsc、vitest+build、Playwright e2e）均已实际运行且全部通过或失败原因已解释清楚；
- 手动核对 `config/settings.json` 在 Web 端保存后的内容与桌面端保存效果一致；
- `pa_agent/gui/` 桌面应用仍可正常启动运行（至少验证 `python run.py` 能进入主窗口，不要求逐项回归全部 GUI 功能）；
- 已生成 `phase-1-completion-report.md` 和 `phase-2-execution-plan.md`（阶段二为"交易记录分析报告页面"，编写该执行方案前须重新打开 `pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg` 核对设计细节，并明确 `trade_logger.py` CSV 到设计图每个指标/图表的取数与计算口径）。

## 9. 停止条件

出现以下情况之一时，必须停止并生成 `partial`/`blocked` 状态的总结报告，而非强行标记完成：

- 依赖安装出现无法自行解决的冲突；
- 需要改动核心业务模块契约但未获用户确认；
- Playwright/pytest 验证出现未解释的失败且排查后仍无法定位根因；
- 任务范围内出现与总纲/本方案矛盾之处，需要用户澄清。
