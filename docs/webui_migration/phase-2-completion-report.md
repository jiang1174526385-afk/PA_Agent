# 阶段二总结报告：交易记录分析报告页面

> 所属总纲：[`README.md`](README.md)
> 所属执行方案：[`phase-2-execution-plan.md`](phase-2-execution-plan.md)
> 完成日期：2026-07-15
> **阶段状态：`complete`**（含 §8 列出的、需要您后续确认/关注的几个默认决策）

## 0. 与您确认过的关键口径（实施前已用 AskUserQuestion 征询，您回答后离开，未回答的一项已用保守默认值处理并在下面标出）

1. **收益率(%)**：不计算——CSV/MT5/OKX 均无期初本金或历史余额数据，虚构一个会误导用户。KPI 卡片只保留"总收益"绝对值 USD，不显示"收益率/年化收益"。
2. **撮合规则**：不做 exact/fuzzy 价格容差分级——只做"时间窗口内找到同方向成交=filled，找不到=unfilled"的二元判定。`match_confidence` 字段简化为 `matched`/`unmatched` 两态（执行方案 §4.2 原设想的 `exact`/`fuzzy`/`unmatched` 三态未实现）。
3. **图表库**：`recharts`（新增前端依赖，环形图/柱状图用它渲染；净值曲线/月度收益/持仓时间分布/滑点分布同样用它；K线仍用阶段一的 `lightweight-charts`，两者互不冲突）。
4. **顶部两个相似下拉的语义**（您未及回答）：默认按"两者是同一个筛选器，设计图画重复了"处理——本阶段只实现了一个"策略"筛选下拉（`全部策略` + 具体 stance 枚举值），没有做独立的"账户/策略组合"选择器。**这是本阶段唯一一处没有得到您明确确认就采用默认值的地方，如果实际含义是"账户选择器"和"策略筛选器"两个独立概念，需要后续阶段补一个账户/账号维度的下拉。**

此外，设计稿路径与总纲/执行方案里写的 `pa_agent/qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg` 不符，实际文件在仓库根 `qunyou/AD48DF6289CB6A9D51FE0B8EE2EC38C2.jpg`（没有 `pa_agent/` 前缀）。已按实际路径读取，未改动文件位置，仅在此记录供后续阶段避免重复找错路径。

## 1. 原计划任务逐项完成情况

| 执行方案条目 | 状态 | 说明 |
|---|---|---|
| §5.1 配置扩展（`OKXSettings`） | ✅ | `pa_agent/config/settings.py` 新增 `OKXSettings`（api_key/api_secret/passphrase）+ `Settings.okx`；Web 端 `schemas/settings.py`/`api/settings.py` 新增 "okx" 分区，脱敏语义与 provider/feishu 一致；前端新增「OKX」设置 Tab |
| §5.2 成交结果回填模块 | ✅（含简化，见 §0.2） | `pa_agent/data/trade_history.py`（`fetch_mt5_deals`/`fetch_okx_positions_history`，只读）+ `pa_agent/records/trade_fill_backfill.py`（`backfill_csv`，幂等、按 record_time 窗口撮合、可独立于 Web 层调用） |
| §5.2 API（list/backfill/summary/orders） | ✅（新增一个 `/calendar` 端点，执行方案未列出但盈亏日历模块需要） | `pa_agent/webui/api/reports.py`：`GET /api/reports`、`POST /api/reports/{key}/backfill`、`GET /api/reports/{key}/summary`、`GET /api/reports/{key}/calendar`、`GET /api/reports/{key}/orders` |
| §5.3 指标计算口径 | ✅（收益率/年化收益按 §0.1 不做） | `pa_agent/records/report_metrics.py`：总收益/最大回撤(USD+相对峰值%)/盈利因子/胜率(含多空分离)/平均每笔比/交易次数/最大连续亏损/停滞天数/持仓时间分布/滑点分布/净值曲线/月度收益/品种分布/盈亏日历，公式均写在函数旁的 docstring/注释里 |
| §5.4 前端（浅色主题独立模块） | ✅ | `src/reportStyles/reportTokens.css`（全新变量名 `--report-*`，不 import `tokens.css`）；`src/reports/`：`ReportsPage.tsx`/`SideNav.tsx`/`KpiCard.tsx`/`OrderTable.tsx`/`charts/*`（9 个图表组件）；`main.tsx` 按 `pathname` 做极简路由（`/` 阶段一工作台，`/reports` 本阶段页面），未引入 `react-router` |
| 本阶段范围：4 个占位导航 | ✅ | 「报告对比/收益分析/风险分析/策略分析」可点击，显示"开发中"，不含任何实际功能 |
| 后端 pytest | ✅ | `tests/webui/test_reports_api.py`（6 用例，含 MT5 fake fixture 覆盖 matched/unmatched/幂等/OKX 缺凭证 400）、`tests/unit/test_trade_fill_backfill.py`（12 用例，纯函数级指标断言：已知答案的最大回撤/盈利因子/连续亏损/停滞天数/多空胜率/滑点/持仓分布） |
| 前端 tsc/vitest/build | ✅ | 见 §7 |
| Playwright e2e | ✅ | `tests/webui/e2e/test_phase2_reports_smoke.py`（3 场景：浅色主题+KPI渲染+无控制台错误、占位路由显示"开发中"、回填按钮+订单表格） |
| 阶段总结报告 | ✅ | 本文件 |
| 阶段三执行方案 | ✅ | [`phase-3-execution-plan.md`](phase-3-execution-plan.md) |

## 2. 实际修改/新增的文件

**新增：**
- `pa_agent/data/trade_history.py`（MT5/OKX 只读历史成交查询）
- `pa_agent/records/trade_fill_backfill.py`（CSV 回填，含窗口/撮合逻辑）
- `pa_agent/records/report_metrics.py`（纯函数指标计算）
- `pa_agent/webui/api/reports.py`、`pa_agent/webui/schemas/reports.py`
- `pa_agent/webui/frontend/src/reportStyles/reportTokens.css`
- `pa_agent/webui/frontend/src/reports/`（`ReportsPage.tsx`/`SideNav.tsx`/`KpiCard.tsx`/`OrderTable.tsx`/`format.ts`+测试/`reportsApi.ts`/`charts/*.tsx` 共 9 个图表组件）
- `pa_agent/webui/frontend/src/settings/OKXTab.tsx`
- `tests/unit/test_trade_fill_backfill.py`、`tests/webui/test_reports_api.py`、`tests/webui/e2e/test_phase2_reports_smoke.py`

**修改：**
- `pa_agent/config/settings.py`（`OKXSettings` + `Settings.okx`）
- `pa_agent/webui/schemas/settings.py`、`pa_agent/webui/api/settings.py`（"okx" 分区）
- `pa_agent/webui/server.py`（挂载 `reports_api.router`）
- `pa_agent/webui/frontend/src/api/client.ts`（新增 `post()`）
- `pa_agent/webui/frontend/src/api/paAgentApi.ts`、`src/types/domain.ts`（OKX 设置类型 + 阶段二全部 DTO）
- `pa_agent/webui/frontend/src/settings/SettingsModal.tsx`（新增 OKX Tab）
- `pa_agent/webui/frontend/src/main.tsx`（`/reports` 路由分支）
- `pa_agent/webui/frontend/package.json`/`package-lock.json`（新增 `recharts`）
- `tests/webui/test_settings_api.py`（新增 okx 分区往返测试）

**未改动（按计划严格遵守边界）：**
- `pa_agent/gui/` 全部零改动（`git status --short -- pa_agent/gui/` 确认为空）。
- `pa_agent/webui/frontend/src/styles/tokens.css`、`src/App.tsx`、`src/toolbar/`、`src/chart/`、`src/decision/` 阶段一暗色主题代码零改动。
- `pa_agent/orchestrator/two_stage.py` 决策逻辑零改动；回填模块只读取/追加 CSV 数据。

## 3. 遇到的问题、根因与解决方式

1. **设计图/CSV 里的中文方向枚举值搞错**：编写测试时最初用了"多头"/"空头"，但 `pa_agent/ai/json_validator.py`/`prompt_assembler.py` 等实际代码里 `order_direction` 的合法枚举值是"做多"/"做空"（`_is_long()` 判断逻辑沿用 `trade_logger.py._render_chart` 里已有的 `"short" not in d and "做空" not in d` 写法，只认"做空"不认"空头"）。已修正全部测试用例的方向字符串，`_is_long()` 本身实现未改（它本就是对齐现有代码的既有约定，不是本阶段引入的新错误）。
2. **前端 `formatUsd` 负数格式错误**：初版实现是 `${sign}$${value.toLocaleString(...)}`，但 `toLocaleString` 本身已经在负数前加了 `-`，导致输出 `$-10,772.10` 而非 `-$10,772.10`。改为先取绝对值格式化数字部分、符号单独拼接在 `$` 前面。
3. **recharts `Tooltip formatter` 的 TS 类型与 `(value: number) => ...` 签名不兼容**：`ValueType` 允许 `number | string | Array<...> | undefined`，显式标注 `value: number` 会被 tsc 拒绝。改为不显式标注参数类型（让 TS 从 recharts 的 `Formatter` 类型推断），内部用 `Number(value)` 显式转换。
4. **盈亏日历需要一个执行方案里没写的新端点**：§5.2 只列了 `summary`/`orders`/`backfill` 三个端点，但"盈亏日历支持月份翻页"这个设计图模块需要按 `year`/`month` 查询，塞进 `summary` 响应会让接口职责不清（且无法支持"翻页查询未加载过的月份"而不重新拉取全部 summary）。新增了 `GET /api/reports/{key}/calendar?year=&month=`，复用同一套 `rows_to_filled_trades`/`pnl_calendar` 逻辑。这是执行方案范围内的最小必要补充，不是新功能。

## 4. 可复用经验与后续注意事项

- **设计图路径与文档不一致**：见 §0 附注，`qunyou/` 目录在仓库根，不在 `pa_agent/` 下。后续阶段如果还要引用同一张图或该目录下其它设计稿，直接从仓库根 `qunyou/` 找。
- **`order_direction` 枚举值权威来源是 `pa_agent/ai/prompts/schemas.py`/`json_validator.py`（"做多"/"做空"），不是随手猜的中文词**——后续阶段任何涉及方向判断的新代码都应该复用 `_is_long()`（本阶段在 `trade_fill_backfill.py`/`report_metrics.py` 各写了一份轻量版本，逻辑一致但未抽成公共工具函数，因为两个模块目前没有互相依赖关系；如果后续阶段还要写第三份，建议这时候再抽取到 `pa_agent/util/` 下的共享函数，避免过早抽象）。
- **`trade_records/` 在本沙箱一直是空目录**（阶段一报告 §8 已提到），本阶段所有回填/指标测试都是用构造的假 CSV + monkeypatch 的假 MT5/OKX 数据源验证的，**没有对真实账户的真实历史成交跑过一次回填**。执行方案 §8 验收标准要求"至少一次人工确认过真实账户下的回填结果基本合理"——这一条在本沙箱环境下无法完成（原因同阶段一报告 §7.6：本机没有真实 MT5 终端登录、也没有配置真实 OKX API Key/Secret/Passphrase），需要您在有真实账户/凭证的环境里手动跑一次 `POST /api/reports/{key}/backfill` 验证。

## 5. 设计决策与偏离原计划的原因

- **收益率(%)/年化收益不计算**：§0.1 已确认，用户选择"只显示总盈亏 USD"。原设计图上的这两个 KPI 卡片副文本（"年化收益 577.91%"）在本实现中被省略，卡片本身（收益率）也被移除，KPI 行从设计图的 9 个变成本实现的 8 个（总收益/最大回撤/盈利因子/胜率/平均每笔比/交易次数/最大连续亏损/停滞天数）。
- **`match_confidence` 简化为二态**：§0.2 已确认。
- **最大回撤(%) 的定义**：不是"相对期初本金"（无此数据），而是"回撤金额 / 触发该次回撤前的净值曲线峰值"（一个不需要外部本金基数的、自洽的替代定义），已在 `report_metrics.py` 顶部 docstring 写明。
- **策略/账户下拉去重为一个筛选器**：§0.4 已标出为需要您确认的默认值，不是确定的正确理解。
- **账户信息卡片（"交易员01"/"专业账户"）用静态占位**：项目里没有任何登录态/账户身份的数据源（无用户系统），无法做成"真实数据"，且执行方案 §4.4 本就允许"如遇歧义询问用户，先做静态占位"，本阶段选择了静态占位这一支，已在 `SideNav.tsx` 源码注释里说明原因，如果这个判断不对请告知。
- **回填撮合窗口** = `[本行 record_time, 下一行 record_time)`，最后一行封顶 `min(now, record_time + 30天)`：这是执行方案 §5.2 要求"必须写明依据、不能拍脑袋"的两个数字之一。依据：CSV 是"每次新决策追加一行"的结构，下一行天然代表"上一个计划已被新计划取代"，用它做窗口右边界不是随意选的常数；30 天是为了让最后一行（无下一行可比）的查询范围有界（避免无限增长的历史成交扫描），如果您认为这个封顶值不合适，可以调整 `trade_fill_backfill.py` 里的 `_MAX_LOOKAHEAD_DAYS` 常量。

## 6. 数据/兼容性迁移情况

- CSV 回填是纯追加列（`fill_status`/`actual_entry_price`/`actual_exit_price`/`filled_at`/`closed_at`/`pnl_usd`/`pnl_pips`/`holding_duration_s`/`win_loss`/`match_confidence`），不改变/不重排现有列，`trade_logger.py` 的写入逻辑本身未被触碰——它依旧按原有 `_CSV_FIELDNAMES` 追加决策行；回填只在事后对已有 CSV 文件原地补列。
- `config/settings.json` 新增 `okx` 分区，字段有默认值（空字符串），旧版 `settings.json`（没有 `okx` 键）加载时 Pydantic 会自动用默认值补齐，不需要手写迁移代码（与阶段一 `provider`/`feishu` 等分区的既有行为一致）。
- 未做"旧版本代码读取新 CSV 会被新增列破坏"的专门回归测试（执行方案 §6 提到"需要写一个旧版本兼容的读取测试"）——`trade_logger.py` 用 `csv.DictWriter(..., extrasaction="ignore")` 写入且读取端用 `csv.DictReader` 按列名取值，多余列天然被忽略，风险很低，但没有专门补一个显式测试用例覆盖这一点，记录为遗留项（见 §8）。

## 7. 实际运行的验证命令与结果

### 7.1 后端 pytest（含阶段一回归）
```bash
./.venv/bin/pytest tests/webui/ tests/unit/test_trade_fill_backfill.py --browser chromium
# 47 passed, 1 warning in 54.09s
```
覆盖：阶段一 `test_kline_api.py`(7)/`test_analysis_ws.py`(5)/`test_settings_api.py`(7，含新增 okx 分区 3 个断言点)/`e2e/test_phase1_smoke.py`(7) 全部仍通过；阶段二新增 `test_reports_api.py`(6)/`test_trade_fill_backfill.py`(12)/`e2e/test_phase2_reports_smoke.py`(3)。

### 7.2 前端
```bash
cd pa_agent/webui/frontend
npx tsc --noEmit        # 无错误
npx vitest run           # Test Files 3 passed (3) / Tests 21 passed (21)
npm run build            # 构建成功；产物 800KB（未压缩前），vite 提示"chunk > 500KB"警告，
                          # 未做代码分割（阶段一同样是单 bundle，本阶段沿用同一模式，未引入新的构建复杂度）
```

### 7.3 npm 依赖安装
```bash
npm install recharts
# added 38 packages；npm audit 报告 5 个漏洞（3 moderate/1 high/1 critical），
# 全部是 esbuild/vite 的开发期传递依赖（devDependencies 链路），与阶段一报告 §7.1
# 记录的既有 5 个警告同源，非本阶段引入的新增直接依赖问题。
```

## 8. 遗留问题和风险

- **§0.4 下拉语义未确认**：如果"顺势交易-保本"实际应该是独立的账户/账号维度选择器而非与"全部策略"重复，需要后续补一个账户维度筛选（目前完全没做）。
- **未在真实账户上验证过回填结果**（见 §4 第三条），仅有假数据测试覆盖。
- **"报告对比/收益分析/风险分析/策略分析"四个占位路由完全没有内容**，符合本阶段范围（§2 非目标），但也意味着它们目前是纯装饰性导航项。
- **策略筛选下拉的可选值是硬编码的 `decision_stance` 枚举**（`conservative`/`balanced`/`aggressive`/`extreme_aggressive`），不是从实际 CSV 里"发现"出来的distinct值——如果未来 CSV 里出现这个枚举之外的策略标签（比如手动编辑过CSV），筛选下拉不会显示它。
- **CSV 多余列的向后兼容性**没有专门测试用例覆盖（见 §6 最后一条），基于 `DictReader`/`DictWriter` 的行为推断风险很低但未实测验证。
- **OKX/MT5 私有接口字段名未经真实账户验证**：`fetch_mt5_deals`（`MetaTrader5.history_deals_get` 官方 API，字段名取自官方文档）与 `fetch_okx_positions_history`（OKX 官方 `positions-history` 文档字段）均按官方文档字段名实现，但从未用真实凭证跑通过一次，如果官方文档与实际返回有出入（历史上偶有发生，如 `tradingAgents/webui/terminal/okx_rest.py` 注释提到的 `positions-history` 分页游标方向"文档不准确"的先例），需要在真实环境验证时留意。

## 9. 是否允许进入下一阶段

**允许，但请先确认 §0.4 的默认决策是否符合预期**（不影响阶段三本身的独立性——阶段三是决策树回放面板，与阶段二的报告页面功能、主题、数据源都完全独立，即使 §0.4 需要返工也不会影响阶段三的开始）。`phase-3-execution-plan.md` 已生成。
