# 阶段二执行方案：交易记录分析报告页面

> 所属总纲：[`README.md`](README.md)
> 上一阶段总结：[`phase-1-completion-report.md`](phase-1-completion-report.md)（状态 `complete`）
> 设计参照：`pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg`（本执行方案编写前已重新打开核对，见 §3.3）
> Session 规则：本执行方案必须在一个独立 Session 中完成；该 Session 不得实施阶段三内容（决策树回放面板）及之后各阶段。

## 0. 与用户确认过的关键决策（写execution方案前已澄清，不得自行更改）

1. **成交结果数据来源**：对接 **MT5/OKX 真实历史成交记录**（不是用K线路径模拟回填）。MT5 用 `MetaTrader5.history_deals_get()`（标准 MT5 Python API，本仓库尚未使用过）；OKX 用私有 REST 端点 `/api/v5/account/positions-history`（需要 API Key/Secret/Passphrase 签名，公共端点如现有 `pa_agent/data/okx_source.py` 用的 `/api/v5/public/instruments` 不需要鉴权，但历史成交属于私有端点，必须鉴权）。
2. **本阶段范围**：只做"总览"一屏（设计图里的全部模块）；左侧导航"报告对比/收益分析/风险分析/策略分析"四项做**路由占位**（可点击，内容显示"开发中"），不实现具体功能。

## 1. 阶段目标

新增一个独立的"交易记录分析报告"页面（`/reports` 或类似路由，前端路由自定），视觉与交互对齐设计图，数据来源为 `trade_logger.py` 写入的 CSV **加上本阶段新增的真实成交结果回填**。这是现有 PyQt6 GUI 中不存在的全新功能。

## 2. 非目标

- 不实现"报告对比/收益分析/风险分析/策略分析"四个子页面的具体功能（仅路由占位 + "开发中"提示）。
- 不实现决策树回放（阶段三）、动画流程图（阶段四）、自由对话/调试面板（阶段五）、演示模式/下单机会通知（阶段六）。
- 不改动阶段一已完成的暗色主题工作台任何代码/样式（`pa_agent/webui/frontend/src/styles/tokens.css` 等），本阶段的浅色仪表盘主题必须完全独立（新建 `src/styles/reportTokens.css` 或等价文件，不 import/复用 `tokens.css`）。
- 不改动 `pa_agent/orchestrator/two_stage.py` 的决策逻辑本身；成交结果回填只读取/追加数据，不影响 AI 决策链路。
- 不对 `config/settings.json` 做除"新增 OKX 私钥字段"外的任何 schema 改动（见 §5.1，且必须脱敏展示，与阶段一密钥处理方式一致）。
- 飞书/PushPlus 实际通知发送、下单机会检测仍不在本阶段范围（阶段六）。

## 3. 前置条件

1. 依次读取 `README.md`、本文件、`phase-1-completion-report.md`（含其 §10 附录：阶段一验收后补做的 Git 仓库迁移记录）。
2. `git status --short`，确认阶段一的改动已按用户要求处理（提交或保留在工作区），不得回滚。阶段一结束时代码已提交至 `main`（`8bd6473`/`3acff71`）并推送到 `origin` = `git@github.com:jiang1174526385-afk/PA_Agent.git`（**不再是**旧的 `rosemarycox5334-debug/PA_Agent.git`），本仓库本地 git 身份已设置为 `jiang1174526385-afk <jiang1174526385-afk@users.noreply.github.com>`，新提交无需重新配置身份；若 `git remote -v` 显示的不是这个地址，说明环境有变化，需要向用户确认而不是假设。
3. 重新打开 `pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg` 核对模块细节（本执行方案编写时已打开一次，见 §3.3 的模块清单，但实施 session 开始时仍需按协议重新打开核对，不能只读本文字描述）。
4. 通读 `pa_agent/records/trade_logger.py` 全文（尤其 `_CSV_FIELDNAMES`、`_render_chart`、写入函数的调用时机），确认 CSV 现有字段（本方案 §4.1 已逐列列出，但实施时仍需核对是否有偏差）。
5. 通读 `pa_agent/data/mt5.py`、`pa_agent/data/okx_source.py` 全文，确认现有 `connect()`/`disconnect()` 生命周期，新增的历史成交查询函数应放在哪个模块（建议新建 `pa_agent/data/trade_history.py`，见 §5.2，不in-place 塞进 `mt5.py`/`okx_source.py` 避免职责混杂，除非发现更好的位置需要说明理由）。
6. 参考 `/home/jack/quant_trading_system_v2/tradingAgents/webui/terminal/okx_rest.py` 中 `_sign()`/`_build_headers()`/`get_positions_history()` 的 OKX 私有端点签名模式（HMAC-SHA256 + `OK-ACCESS-KEY/SIGN/TIMESTAMP/PASSPHRASE` 四个 header），作为实现参考，不直接复制其 async/httpx 依赖，用本项目已有的 HTTP 客户端风格改写。

## 4. 当前代码事实（实施时仍需按需核实）

### 4.1 `trade_logger.py` 现有 CSV 字段（`_CSV_FIELDNAMES`，共 5 组）

Meta：`record_time`/`symbol`/`timeframe`/`decision_stance`/`model`
决策核心：`order_direction`/`order_type`/`entry_price`/`stop_loss_price`/`take_profit_price`/`take_profit_price_2`/`entry_rule`/`entry_basis_bar`/`entry_basis_extreme`
置信度与胜率：`diagnosis_confidence(_reasoning)`/`trade_confidence(_reasoning)`/`estimated_win_rate(_reasoning)`
理由与因子：`reasoning`/`key_factors`/`watch_points`/`risk_assessment`/`invalidation_condition`
诊断摘要/Stage2 bar分析/下一周期预测/终局/延续性审计/图片路径：略（详见源码，未改动）

**关键结论：这些字段全部是"AI 做出决策时的计划快照"，不包含任何"该计划是否被执行/何时执行/出场价/实际盈亏"。`trade_records/` 目录当前为空，没有可参考的历史样本。**

### 4.2 需要新增的"成交结果"字段（本阶段设计，实施时按此追加到 CSV，不删除/重命名现有列）

| 新增列 | 含义 | 取数来源 |
|---|---|---|
| `fill_status` | `unfilled`/`filled`/`expired`/`unknown` | 用 MT5 `history_deals_get`/OKX `positions-history` 按 `symbol`+`record_time` 之后的时间窗匹配 |
| `actual_entry_price` | 实际成交入场价 | 同上，取匹配到的 deal/position 的 `price`/`avgPx` |
| `actual_exit_price` | 实际出场价 | 同上 |
| `filled_at` / `closed_at` | 成交/平仓时间（ISO + ms） | 同上 |
| `pnl_usd` | 已实现盈亏（USD/账户结算币种） | MT5 `profit` 字段 / OKX `pnl` 字段 |
| `pnl_pips` | 盈亏点数 | `(actual_exit_price - actual_entry_price)` 按方向换算 |
| `holding_duration_s` | 持仓秒数 | `closed_at - filled_at` |
| `win_loss` | `win`/`loss`/`breakeven` | `pnl_usd` 符号 |
| `match_confidence` | `exact`/`fuzzy`/`unmatched` | 撮合算法的匹配置信度（见 §5.2 撮合规则），避免时间/价格误差导致的错配被当成"精确匹配"处理 |

### 4.3 鉴权缺口

`pa_agent/config/settings.py` 当前**没有** OKX 的 API Key/Secret/Passphrase 字段（`OKXSource` 目前只用公共端点，无需鉴权）。查询私有成交历史必须新增 `OKXSettings`（`api_key`/`api_secret`/`passphrase`，均为脱敏密钥字段，处理方式与 `provider.api_key`/`feishu.secret` 完全一致：`mask_secret()`、`GET` 不回显明文、`PUT` 用 `None`=不变/`""`=清空语义）。这是"因 Web 端暴露需要新增"的最小必要 schema 改动，符合总纲 §2 允许的例外条件。

MT5 侧 `MetaTrader5.history_deals_get(date_from, date_to)`/`history_orders_get(...)` 是标准 MT5 Python API 自带方法，只要 `mt5.initialize()` 成功（现有 `MT5Source.connect()` 已做），不需要新增配置。

### 4.4 设计图模块清单（`AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg`，总览一屏，本方案编写时已核对像素/配色/字号，实施时需再核对一次）

顶部：标题「交易记录分析报告」+ 面包屑「账户表现 / 风险控制 / 交易质量 / 订单复盘」+ 日期范围选择器（示例默认 `2025-01-02 ~ 2026-06-30`）+ 策略下拉（示例「顺势交易-保本」）+ 品种下拉（「全部品种」）+ 策略下拉（「全部策略」，与前一个策略下拉是否重复需实施时向用户确认，设计图上出现了两处近似的下拉，可能一个是策略一个是账户）+「管理报告」按钮。

9 个 KPI 卡片（左到右）：总收益（$162,334.10，图标为货币）、收益率（+1,623.34%，含"年化收益 577.91%"副文本）、最大回撤（-10.95%，副文本"回撤金额 10,772.10"）、盈利因子（2.01，图标天平）、胜率（67.03%，副文本"胜 / 负 311 / 153"）、平均每笔比（0.99 : 1，副文本"平均盈利/平均亏损"）、交易次数（464，副文本"日均交易 2.08"）、最大连续亏损（4，副文本"当前筛选范围"）、停滞天数（79 天，副文本"最长修复,尚未恢复"）。

图表区（第二行）：净值曲线（折线，双 Y 轴：净值USD + 基准%，右上角 近7天/近30天/近90天/全部 时间切换）；月度收益（柱状图，USD，含负值月份）；品种分布（环形图，按品种净收益绝对值占比，示例单一品种 100%）。

第三行：盈亏日历（月历热力图，逐日盈亏数值，支持左右翻页月份，左侧有"周期统计周期"侧栏显示总区间）；交易概览（环形图，多头/空头净收益对比）；交易方向分析（两个并排环形图：多头胜率/空头胜率，各自标注笔数）；盈亏概览（环形图，盈利笔数/亏损笔数）；持仓时间分布（柱状图，≤15分钟/15-60分钟/1-2小时/2-4小时/>4小时 五档，含各档占比%）；执行质量/滑点分布（柱状图 + 顶部"平均滑点 +42.35点"指标，五档 +5/+15/+25/+35/≥+40）。

底部：订单明细表格，列：时间/品种/方向/入场价/出场价/手数/盈亏(USD)/盈亏(点)/持仓时长/策略/备注，右上角搜索框+排序下拉+全部订单筛选下拉+导出全部按钮，右下角分页（示例"共464笔"/"第1/47页"）。

左侧竖排图标导航：总览（当前高亮）/报告对比/收益分析/风险分析/策略分析/设置。底部账户信息卡片（头像+"交易员01"+"专业账户"）——本阶段是否需要这个账户卡片的真实数据源，还是先做静态占位，实施时如遇歧义需询问用户。

## 5. 实施步骤

### 5.1 配置扩展（最小必要）
1. `pa_agent/config/settings.py`：新增 `OKXSettings(BaseModel)`（`api_key`/`api_secret`/`passphrase`，均 `str = ""`）+ 挂到根 `Settings.okx`；`load_settings`/`save_settings` 自动覆盖（Pydantic 会自动处理新增字段，只要给默认值，不需要手写迁移逻辑）。
2. `pa_agent/webui/schemas/settings.py`：新增 `OKXRead`/`OKXWrite` + `okx_to_read`/`apply_okx_write`，复用 `mask_secret()`；`pa_agent/webui/api/settings.py` 的 `_READERS`/`_WRITE_MODELS`/`_APPLIERS` 增加 `"okx"` 分区。前端 `SettingsModal` 增加第五个 Tab「OKX」（三个 `SecretInput`）。

### 5.2 成交结果回填模块
3. 新建 `pa_agent/data/trade_history.py`：
   - `fetch_mt5_deals(symbol, ts_from_ms, ts_to_ms) -> list[dict]`：包 `MetaTrader5.history_deals_get`，转成统一的内部 dict（`price`/`profit`/`time`/`volume`/`entry`(in/out) 等 MT5 原生字段名先保留，不强行套用 OKX 命名）。
   - `fetch_okx_positions_history(inst_id, after, before) -> list[dict]`：参照 `tradingAgents/webui/terminal/okx_rest.py` 的签名逻辑（HMAC-SHA256，四个 header），用 `OKXSettings` 提供的密钥；调用 `/api/v5/account/positions-history`。
   - 两个函数都只读，不下单/不撤单。
4. 新建 `pa_agent/records/trade_fill_backfill.py`：
   - `backfill_csv(csv_path, kind) -> BackfillResult`：读取 CSV 各行，跳过已回填（`fill_status` 非空）的行；按 `record_time` 之后一个时间窗口（例如到下一条记录的 `record_time`，或固定 N 小时，需要在实施时明确窗口大小的取值依据，不能拍脑袋定一个数字而不解释）查询 §5.2.3 的历史成交；撮合规则：同 `symbol`、方向一致、`entry_price` 在实际成交价的容差范围内（容差取值同样需要写明依据，如"该品种最小报价单位的 N 倍"）→ 判定 `match_confidence="exact"`；容差外但时间窗内唯一一笔同方向成交 → `"fuzzy"`；无匹配 → `fill_status="unfilled"`，`match_confidence="unmatched"`。
   - 回填结果写回 CSV（追加列，见 §4.2），保留原有列不变，不重排/不删除历史行。
   - 该模块应可独立于 Web 层单独调用（CLI 或定时任务均可复用），不要把回填逻辑写进 API handler 里。
5. `pa_agent/webui/api/reports.py`：`POST /api/reports/{symbol}_{timeframe}/backfill`（触发一次回填，返回本次处理的行数/匹配数/未匹配数）；`GET /api/reports/{symbol}_{timeframe}/summary?from=&to=&strategy=`（读取回填后的 CSV，计算 §5.3 的全部聚合指标）；`GET /api/reports/{symbol}_{timeframe}/orders?...`（订单明细表格用，支持分页/排序/筛选/搜索）。

### 5.3 指标计算口径（每个都要在代码里写清楚公式，不能"看起来对"就了事）
- 总收益 = Σ `pnl_usd`（仅 `fill_status=="filled"` 且 `win_loss` 非空的行）。
- 收益率 = 总收益 / 期初净值基数；年化收益 = 收益率按实际交易日数折算到 365 天（需要明确"期初净值基数"从哪来——如果没有账户余额数据，可能只能算"相对于总入金"的收益率，这是一个需要在实施 session 向用户确认的口径问题，不要自行假设一个初始本金）。
- 最大回撤 = 净值曲线（按 `closed_at` 排序累加 `pnl_usd`）历史最高点到之后最低点的最大跌幅，含回撤金额和百分比两种表示。
- 盈利因子 = Σ盈利笔 `pnl_usd` / |Σ亏损笔 `pnl_usd`|。
- 胜率 = 盈利笔数 / (盈利笔数+亏损笔数)；同时给出多头胜率/空头胜率（按 `order_direction` 分组）。
- 平均每笔比 = 平均每笔盈利 / 平均每笔亏损（绝对值比）。
- 交易次数 = `fill_status=="filled"` 的行数；日均交易 = 交易次数 / 覆盖自然日数。
- 最大连续亏损 = 按 `closed_at` 排序后最长的连续 `win_loss=="loss"` 计数。
- 停滞天数 = 从最近一次创净值新高到当前（或当前筛选范围末尾）的自然日数。
- 持仓时间分布 = 按 `holding_duration_s` 分桶（≤15min/15-60min/1-2h/2-4h/>4h）计数占比。
- 滑点 = `actual_entry_price` 与计划 `entry_price` 的差值（按点值换算），平均滑点/中位滑点 + 分桶柱状图（+5/+15/+25/+35/≥+40，具体分桶边界以设计图为准，实施时核对）。

### 5.4 前端（浅色主题，独立模块）
6. `pa_agent/webui/frontend/src/reportStyles/reportTokens.css`：全新浅色卡片仪表盘配色（白底、圆角卡片），不 import 阶段一 `tokens.css`。
7. `src/reports/`：`ReportsPage.tsx`（顶部筛选栏+KPI卡片行+图表网格+订单表格）、`SideNav.tsx`（竖排图标导航，总览高亮+四个占位路由）、`KpiCard.tsx`、图表组件（复用阶段一已引入的图表库能力或按需新增柱状图/环形图/热力图库——`lightweight-charts` 主打K线，环形图/柱状图/热力图需要评估是否用它还是新增轻量库如 `recharts`/手写 SVG，实施时需要说明选型理由）、`OrderTable.tsx`（搜索/排序/筛选/导出/分页）。
8. 路由：新增一个极简的 client-side 路由判断（`/` = 阶段一工作台，`/reports` = 本阶段报告页），不引入 `react-router` 等重量级依赖除非确认必要。

## 6. 兼容策略与回滚点

- 所有新增代码位于 `pa_agent/data/trade_history.py`、`pa_agent/records/trade_fill_backfill.py`、`pa_agent/webui/api/reports.py`、`pa_agent/webui/frontend/src/reports*`；回滚只需删除这些路径 + 还原 `config/settings.py`/`schemas/settings.py`/`api/settings.py` 的 OKX 分区新增段落。
- CSV 回填是**追加列**，不改变现有列语义，旧版本代码读取新 CSV 时只是忽略新增列，不会崩溃（需要在实施时写一个"旧版本兼容"的读取测试验证这一点）。
- 若发现 MT5/OKX 历史成交接口在实际调用中限制严格（如 OKX `positions-history` 只保留 3 个月数据、MT5 `history_deals_get` 单次查询上限），必须停下记录影响范围，不得静默截断数据后当作"完整回填"呈现给用户。

## 7. 测试与验证命令

- 后端 pytest：`tests/webui/test_reports_api.py`（注入假的 MT5/OKX 历史数据 fixture，覆盖回填撮合规则的 exact/fuzzy/unmatched 三种情况）、`tests/unit/test_trade_fill_backfill.py`（纯函数级指标计算：最大回撤/盈利因子/连续亏损/停滞天数，用构造好的已知答案的 `pnl_usd` 序列断言）。
- 前端：`tsc --noEmit`/`npm run build`/`npx vitest run`（图表数据转换函数、KPI 计算的前端展示格式化函数）。
- Playwright e2e：`tests/webui/e2e/test_phase2_reports_smoke.py`——打开 `/reports`，断言浅色主题生效（背景色与阶段一暗色不同）；断言 9 个 KPI 卡片渲染且数值非 `NaN`/`undefined`；切换日期范围/品种筛选后请求参数正确；点击"报告对比"等占位导航显示"开发中"且不报错；订单表格分页/排序/导出可用；全程 `.venv` 内运行，缺依赖按 §7.1 原则处理。

## 8. 验收标准

- §7 全部验证已实际运行且通过或失败原因已解释清楚。
- 回填模块对 MT5/OKX 两种数据源均有对应测试（用假数据，不依赖真实账户网络调用作为 CI 门禁，但需要至少一次人工确认过真实账户下的回填结果基本合理）。
- 阶段一暗色主题/工作台功能未受影响（回归验证 `tests/webui/`、`tests/webui/e2e/test_phase1_smoke.py` 仍然全部通过）。
- KPI 计算口径已在代码注释或文档中写明公式来源，不存在"魔法数字"。
- 已生成 `phase-2-completion-report.md` 和 `phase-3-execution-plan.md`。

## 9. 停止条件

- OKX/MT5 历史成交接口的实际返回字段与本方案假设的字段名不符，且无法通过官方文档确认时，必须暂停向用户确认，不得凭猜测字段名硬编码。
- "期初净值基数"（收益率分母）没有现成数据来源时，必须暂停向用户确认口径，不得虚构一个初始本金。
- 撮合容差（价格/时间窗口）的取值缺乏依据时，必须暂停向用户确认，不得随意设一个数字。
- 图表库选型（环形图/柱状图/热力图）如需引入新依赖，必须先向用户说明选型理由并确认，不得默认安装了事。
