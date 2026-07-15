# 阶段一总结报告：基础设施 + MVP 核心闭环

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-1-execution-plan.md`](phase-1-execution-plan.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| 5.1 后端骨架（`server.py`/`deps.py`） | ✅ | `lifespan` 内调用 `AppContext.bootstrap()`，构建 `TwoStageOrchestrator`/`AnalysisRunner`；CORS 允许 `localhost:5173`；SPA fallback + `/assets` 静态挂载 |
| 5.2 K线数据流（`RefreshBroadcaster`/`/ws/kline`） | ✅ | 含 epoch 过期帧过滤、指数退避（0.5s→10s，与 `RefreshLoop` 常量一致）、REST symbols/timeframes/snapshot |
| 5.3 AI 分析流（`AnalysisRunner`/`/ws/analysis`） | ✅ | 单飞、全部回调类型透传、取消（含断线自动取消）、异常兜底 |
| 5.4 设置 API | ✅ | provider/general/feishu/pushplus 四分区，密钥脱敏 + `xxx_set`，`PUT` 支持 `None`=不变/`""`=清空 |
| 5.5 前端骨架 | ✅ | Vite+React19+TS，`appStore`（Context+useReducer）、`paAgentApi`/`paAgentWs`（含重连退避+epoch过滤） |
| 图表/Toolbar/DecisionPanel/FutureTrendPanel/设置弹窗 | ✅ | lightweight-charts 蜡烛图+EMA20/ATR14；决策价格线（entry/TP1/TP2/SL）；四个设置 Tab |
| 5.6 入口与工具链 | ✅ | `pyproject.toml` 新增 `webui`/`dev` 依赖组；`start_webui.py`；`Makefile` 新增 3 个 target |
| pytest（后端） | ✅ | `tests/webui/`：18 个用例全部通过 |
| tsc/vitest/build（前端） | ✅ | `tsc --noEmit` 无错误；`vitest run` 8/8 通过；`npm run build` 成功 |
| Playwright e2e | ✅ | `tests/webui/e2e/`：7/7 场景通过（真实 Chromium） |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段二执行方案 | ✅ | [`phase-2-execution-plan.md`](phase-2-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增（未纳入版本控制前均为 untracked）：**
- `pa_agent/webui/`：`server.py`、`deps.py`、`api/{kline,analysis,settings,models}.py`、`services/{refresh_broadcaster,analysis_runner}.py`、`schemas/{kline,settings}.py`、`static/pa_agent_app/`（构建产物，已加入 `.gitignore`）
- `pa_agent/webui/frontend/`：完整 Vite+React+TS 项目（`src/{state,api,chart,toolbar,decision,settings,styles,types}/`、`App.tsx`、`main.tsx`）
- `tests/webui/`：`conftest.py`（`FakeDataSource`）、`test_kline_api.py`、`test_analysis_ws.py`、`test_settings_api.py`、`e2e/{conftest.py,test_phase1_smoke.py}`
- `start_webui.py`

**修改：**
- `pyproject.toml`：新增 `[project.optional-dependencies].webui`（fastapi/uvicorn/websockets）与 `dev` 组新增 pytest-asyncio/playwright/pytest-playwright；`[tool.pytest.ini_options]` 加 `asyncio_mode = "auto"`
- `Makefile`：新增 `run-webui`/`dev-webui-frontend`/`build-webui-frontend`
- `.gitignore`：新增前端 `node_modules/`/`dist/` 与后端构建产物 `static/pa_agent_app/*` 忽略规则

**未改动（按计划严格遵守边界）：**
- `pa_agent/orchestrator/`、`pa_agent/data/`（除 `okx_source.py` 是本 session 开始前已存在的未提交 WIP，未被本阶段触碰）、`pa_agent/indicators/`、`pa_agent/config/`（同上，`settings.py` 的改动是既有 WIP）、`pa_agent/records/`、`pa_agent/notify/`、`pa_agent/gui/` 全部零改动。

## 3. 遇到的问题、根因与解决方式

1. **`/ws/kline` 帧含 `NaN` 导致浏览器 `JSON.parse` 崩溃**
   根因：EMA20/ATR14 warm-up 期的值为 Python `float('nan')`，`json.dumps`/`ws.send_json` 默认 `allow_nan=True` 会输出裸 `NaN` 字面量，这不是合法 JSON，Chrome 的 `JSON.parse` 直接抛异常导致页面崩溃且后续所有帧都无法解析。
   解决：`schemas/kline.py::_nan_to_none()` 在序列化时把 NaN 换成 `null`；前端 `IndicatorBundle` 类型改为 `(number|null)[]`，图表侧过滤 `null` 点后再渲染折线。

2. **默认数据源 `mt5` 导致页面一加载就发出必然失败的请求**
   根因：`GeneralSettings.last_data_source` 默认值是 `"mt5"`，而 `MetaTrader5` 是 Windows-only 包，本沙箱（以及任何未登录 MT5 终端的机器）上 `connect()` 必然抛 `DataSourceTransientError`，前端若照搬这个默认值会在挂载时自动请求一个必然 500 的接口。
   解决：前端 `defaultAppState.source` 改为空字符串，数据源下拉增加"选择数据源"占位项，强制用户显式选择后才发起请求；同时给 `fetchSymbols`/`fetchTimeframes` 补上 `.catch()`，避免未捕获 Promise 拒绝污染控制台。这是一个真实的可用性问题（不仅影响本沙箱，任何 MT5 终端未运行的桌面环境都会遇到），已在实现阶段直接修正，不留到阶段二。

3. **"提交分析"按钮可在 WS 尚未推送首帧前被点击，导致 `/ws/analysis` 立即返回"暂无K线数据"**
   根因："获取数据"点击后前端会立刻用 REST `/api/kline/snapshot` 渲染出蜡烛图（体验更快），但服务端 `/ws/analysis` 判断"是否有可用K线"依据的是 `/ws/kline` 广播器内部维护的 `latest_frame`，二者是两条独立通路，图表渲染完成不代表广播器已经产出过一帧。
   解决：Toolbar 新增 `hasFrame` 门控，"提交分析"/"增量分析"按钮改为在收到至少一帧 `/ws/kline` 广播后才可点击，而不仅仅依赖 symbol/timeframe 是否选中。

4. **设置表单的 `<label>` 与 `<input>` 未关联，Playwright `get_by_label`/屏幕阅读器均无法定位**
   根因：`.form-row` 内 `<label>` 与 `<input>` 是兄弟节点，没有 `htmlFor`/`id` 配对（也没有把 input 包在 label 内）。
   解决：`GeneralTab`/`ProviderTab`/`FeishuTab`/`SecretInput` 补齐 `htmlFor`/`id`；这同时修复了一个可访问性缺陷，不只是测试可寻址性问题。

5. **`tradingAgents/webui` 参照架构里没有 epoch 防乱序机制**（调研阶段发现，非本阶段代码问题）
   `tradingAgents` 的 WS 客户端只有固定 3 秒重连，没有 epoch/版本号过滤过期帧；本阶段按 `phase-1-execution-plan.md` 自身要求实现了 epoch 字段（每次 `subscribe` 自增，客户端丢弃陈旧 epoch 的帧），比参照项目更严格，属于按既定计划执行，不是偏离。

## 4. 可复用经验与后续注意事项

- **`pa_agent/gui/theme/tokens.py` 不是完整调色板**：`decision_panel.py`/`future_trend_panel.py` 里还硬编码了若干未登记进 `tokens.py` 的颜色（如 `#58a6ff`/`#3fb950`/`#f85149`/`#e6b800`/`#a371f7`/`#79c0ff`/`#c9d1d9`）。本阶段 `DecisionPanel.tsx`/`FutureTrendPanel.tsx` 已按桌面端实际显示效果补上这些颜色（未逐一在 `tokens.css` 注册，因为它们本就不属于官方 token 集合），后续阶段若要继续对齐桌面 GUI 的其它面板颜色，需要同样先读实际 widget 源码而非只读 `tokens.py`。
- **`EventBus.emit()` 是桌面端的一个潜在 bug**（`pending_writer.py:171` 调用了不存在的 `event_bus.emit(name, payload)` 方法，被外层 `except Exception` 静默吞掉）：本阶段 Web 端未复刻这个错误路径（`AnalysisRunner` 直接用真实存在的回调发送 WS 消息），但如果后续阶段要"忠实复刻"桌面端行为，需要注意这是桌面端本身的缺陷而非规范。
- **`OrchestratorEvent.InsufficientData` 没有桌面端标签**：`_AnalysisWorker._EVENT_LABELS` 里没有这个枚举值的映射，桌面端会退化成显示 `str(event)`；Web 端 `AnalysisRunner._EVENT_LABELS` 按相同方式保留了这个差距（未额外发明标签），因为擅自新增文案会造成两端不一致，若需要补齐应作为独立小改动并说明理由。
- **本地 `.venv`（Python 3.13 / Linux）与项目实际目标环境（Windows / Python 3.11+）不同**：`MetaTrader5`、`pywin32` 等 `sys_platform == 'win32'` 依赖在本沙箱不安装，`pytest -m "not e2e"` 全量跑一次可发现大量既有失败（见 §7），均与本阶段 diff 无关，但后续阶段如果要在同一沙箱验证 MT5 相关路径，需要向用户确认是否有其它验证手段。

## 5. 设计决策与偏离原计划的原因

- **数据源/K线获取拆成"REST 一次性快照 + WS 持续推送"两条通路**：执行方案本身就是这样设计的（`GET /api/kline/snapshot` 与 `WS /ws/kline` 均在 5.2 列出），非本阶段新增决策；但由此引出的"提交分析要等 WS 帧"这个约束是实现过程中发现并解决的（见 §3.3），已记录。
- **`test_data_sources_api.py` 未单独建文件**：执行方案 §7.2 建议的文件名是 `test_data_sources_api.py`/`test_kline_api.py`/`test_settings_api.py`/`test_analysis_ws.py` 四个文件；实际实现中把数据源列表/symbols/timeframes 的测试合并进了 `test_kline_api.py`（因为它们和 K线快照共用同一个 `pa_agent/webui/api/kline.py` 路由模块和同一份 `FakeDataSource` fixture），未单独起 `test_data_sources_api.py`。功能�covered 无缺失，仅文件切分方式不同，记录在此供后续阶段参考。
- **`GeneralTab` 用配置驱动的字段列表渲染 21 个通用设置项**，未逐项手写 21 个 JSX 块，以保持可维护性；未在执行方案中明确要求这种实现方式，但未偏离任何验收标准。

## 6. 数据/兼容性迁移情况

- 未涉及任何历史数据迁移。`config/settings.json` 的 schema 完全复用 `pa_agent/config/settings.py` 现有 Pydantic 模型，Web 端 `GET/PUT` 只是这些模型的脱敏视图，未新增/删除任何字段。
- `pa_agent/gui/` 桌面应用的行为未被触碰；本阶段全程未修改 `pa_agent/gui/` 下任何文件（`git status` 可验证）。

## 7. 实际运行的验证命令与结果

### 7.1 依赖安装
```bash
cd /home/jack/quant_trading_system_v2/PA_Agent
source .venv/bin/activate
pip install -e ".[dev,webui]"      # 成功，无版本冲突
python -m playwright install chromium   # 成功
cd pa_agent/webui/frontend && npm install   # 成功（5 个预置的第三方包安全警告，均为 dev 依赖传递性警告，非本阶段引入的直接依赖问题）
```

### 7.2 后端 pytest
```bash
./.venv/bin/pytest tests/webui/ -m "not e2e"
# 18 passed, 7 deselected, 1 warning in 0.88s
```

### 7.3 前端静态检查
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无输出，无错误
npx vitest run           # Test Files 2 passed (2) / Tests 8 passed (8)
npm run build            # 构建成功，产物写入 ../static/pa_agent_app/
```

### 7.4 Playwright 端到端（真实 Chromium）
```bash
./.venv/bin/pytest tests/webui/e2e/ --browser chromium
# 7 passed
```
覆盖场景：暗色主题+无控制台错误；切换 TradingView/OKX 数据源联动 symbol/timeframe（MT5 见下方"环境限制"）；获取数据渲染蜡烛图+收到 `/ws/kline` 帧；提交分析→DecisionPanel 从等待态到结果态+生成 `records/pending/*.json`；分析中途取消→UI 回到 idle；设置弹窗密钥脱敏+修改通用字段后刷新页面仍生效；分析中关闭页面→`WebSocketDisconnect` 正确触发取消（无孤儿轮询）。

`TwoStageOrchestrator.submit` 在 e2e 中被 monkeypatch 成确定性 fake（见 `tests/webui/e2e/conftest.py`），因为跑通真实 DeepSeek 两阶段分析需要付费 API Key、且真实网络调用不确定性太高，不适合作为 UI 接线正确性的验收手段；除这一处，其余组件（`AppContext.bootstrap()`、真实 OKX/TradingView 网络数据源、真实 FastAPI/uvicorn 进程、真实 SPA 构建产物）均未 mock。

### 7.5 全量 `pytest -m "not e2e"`（含既有测试）——环境限制说明
在本阶段 diff 之外，仓库全量测试还有大量**与本阶段无关的既有失败**（`test_akshare_live`/`test_deepseek_client`/`test_decision_panel`/`test_mt5_clock_skew`/`test_decision_continuity` 等，共约 50+ 项）。已通过 `git status --short` 确认本阶段未改动这些模块的任何依赖文件；根因是本沙箱环境（Linux/Python 3.13，无真实 MT5 终端、部分 Windows 专属分支代码）与项目实际目标环境（Windows）不一致，以及个别用例本身依赖真实网络/真实 API Key。这些失败在本阶段开始前就已存在，不属于阶段一引入的回归，未在本阶段范围内修复（超出"只重写表现层"的边界）。

### 7.6 `pa_agent/gui/` 兼容性验证——环境限制说明
当前沙箱是无显示的 headless Linux，无法实际弹出 PyQt6 主窗口（既没有 X server，也不适合用 `QT_QPA_PLATFORM=offscreen` 冒充"验证过 GUI 能用"——offscreen 模式下窗口渲染但用户看不到任何实际界面，不能等同于真机验证）。经与用户确认，本阶段不做桌面 GUI 实机启动验证；改为验证 `git status --short` 确认 `pa_agent/gui/` 目录下 0 个文件被本阶段改动，作为"未破坏桌面端"的证据。**这是环境限制导致的验证方式调整，不是跳过验收**：如果需要在真机上做实际验证，需要用户在有显示的 Windows/桌面环境中执行 `python run.py`。

## 8. 遗留问题和风险

- **风险（低）**：`/ws/kline` 的 `RefreshBroadcaster` 每个 `(source, symbol, timeframe)` key 各自持有独立的 `DataSource` 连接；如果同一浏览器标签快速反复切换品种，短时间内可能有多个 OKX/TradingView 连接同时建立又释放。桌面端是单一 `RefreshLoop`/单一连接，没有这个并发场景。当前实现功能正确（新订阅前会先拆除旧 key，若旧 key 还有其它订阅者才保留），但在阶段二/三涉及更复杂交互前，如果发现连接抖动问题，需要考虑连接池/防抖。
- **待办（不阻塞验收）**：`AnalysisRunner`/`RefreshBroadcaster` 目前没有对同一浏览器多标签页共享同一条 K线/分析连接做合并（`tradingAgents` 的 `OKXWSManager` 用了引用计数式共享连接；本阶段每个 WS 连接各自独立）。单用户本地场景下影响很小，但若未来要支持多标签页同时开着监控面板，需要重新设计成引用计数注册表。
- **待办**：`GET /api/ai/models` 目前是硬编码的精选列表（`deepseek-v4-flash`/`deepseek-chat`/`deepseek-reasoner`），因为 `pa_agent/ai/client_factory.py` 没有真正的模型枚举接口；前端已允许自由文本输入作为兜底,但若未来接入更多 provider，需要重新评估这个列表的维护方式。
- **不阻塞，供阶段二参考**：`trade_records/` 目录当前为空，`trade_logger.py` 的 CSV 只记录 AI 决策/挂单计划，不含实际成交结果（详见 `phase-2-execution-plan.md` §4 的数据口径设计）。

## 9. 是否允许进入下一阶段

**允许。** 阶段一验收标准（§7 四类验证均已实际运行且通过、`config/settings.json` Web/桌面写入语义一致、`pa_agent/gui/` 零改动、无未记录的临时实现）已满足。`phase-2-execution-plan.md` 已生成。

## 10. 附录：Git 仓库与提交记录（阶段一验收通过后，应用户要求补做）

阶段一代码验收通过后，用户要求把改动提交并推送到独立的 GitHub 仓库，过程记录如下（供阶段二 session 了解当前仓库状态，不属于阶段一执行方案原定任务，但直接影响阶段二开始时的 `git status`/远程基线）：

1. **本地 git 身份**：本机之前从未配置过 `user.name`/`user.email`，无法提交。最终确认使用 GitHub 账号 `jiang1174526385-afk` 对应的 noreply 邮箱，仅在本仓库（非 `--global`）设置：
   ```
   git config user.name "jiang1174526385-afk"
   git config user.email "jiang1174526385-afk@users.noreply.github.com"
   ```
2. **提交拆分为两个逻辑单元**：
   - `8bd6473`「Add OKX data source support」——本 session 开始前就已存在的未提交 OKX 数据源接入改动（`config/settings.py`/`data/factory.py`/`data/market_defaults.py`/`data/okx_source.py`/对应测试），与阶段一 Web UI 工作是两件事，分开提交。
   - `3acff71`「Add PA Agent web UI phase 1: FastAPI + React MVP workbench」——本阶段全部新增/修改文件。
   - 这两个 commit 最初误用了参照 `tradingAgents` 项目习惯的身份（`Jack <jack@tradingagents.local>`），确认后用 `git rebase -r 33170ab --exec 'git commit --amend --author=...'` 改写为正确身份（此时尚未推送到任何远程，改写历史安全）。
3. **远程仓库**：原有 `origin` 指向 `https://github.com/rosemarycox5334-debug/PA_Agent.git`（这是一个和当前操作者不同的 GitHub 账号）。应用户要求，新建了一个独立仓库 `git@github.com:jiang1174526385-afk/PA_Agent.git` 并把 `origin` 改指向它。
4. **推送冲突与强推**：首次 `git push -u origin main` 被拒绝——新仓库并非空仓库，已有与本地一致的历史（直到 `33170ab`）外加一个本地没有的提交 `99cc780`（`Update README QQ group number to 975328619.`）。已向用户说明这个差异，用户确认该仓库内容不重要，选择 `git push -u origin main --force` 覆盖，`99cc780` 被丢弃。
5. **验证 SSH 认证**：推送前用 `ssh -T git@github.com` 确认过 SSH key 已经能以 `jiang1174526385-afk` 身份认证成功。

**阶段二开始时需要注意**：
- `git remote -v` 现在应显示 `origin` 为 `git@github.com:jiang1174526385-afk/PA_Agent.git`（不再是 `rosemarycox5334-debug`）。
- 后续新提交会自动沿用本仓库已设置的 `jiang1174526385-afk` 身份，无需重新配置。
- `main` 分支本地与远程已同步（`3acff71`），阶段二 session 开始时的 `git status --short` 预期应为空（除非用户在两次 session 之间又做了其它本地改动）。
