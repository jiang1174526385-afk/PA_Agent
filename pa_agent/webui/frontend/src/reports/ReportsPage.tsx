import { useEffect, useMemo, useState } from "react";
import "../reportStyles/reportTokens.css";
import type { ReportListItem, ReportSummaryResponse } from "../types/domain";
import { fetchReportsList, fetchReportSummary, triggerBackfill } from "./reportsApi";
import { KpiCard } from "./KpiCard";
import { SideNav, type ReportsNavKey } from "./SideNav";
import { EquityCurveChart } from "./charts/EquityCurveChart";
import { MonthlyReturnsChart } from "./charts/MonthlyReturnsChart";
import { SymbolDistributionChart } from "./charts/SymbolDistributionChart";
import { PnlCalendar } from "./charts/PnlCalendar";
import { TradeOverviewChart } from "./charts/TradeOverviewChart";
import { DirectionAnalysisChart } from "./charts/DirectionAnalysisChart";
import { PnlOverviewChart } from "./charts/PnlOverviewChart";
import { HoldingTimeChart } from "./charts/HoldingTimeChart";
import { SlippageChart } from "./charts/SlippageChart";
import { OrderTable } from "./OrderTable";
import { formatPct, formatRatio, formatUsd } from "./format";

export function ReportsPage() {
  const [nav, setNav] = useState<ReportsNavKey>("overview");
  const [reports, setReports] = useState<ReportListItem[]>([]);
  const [selectedKey, setSelectedKey] = useState<string>("");
  const [strategy, setStrategy] = useState<string>("__all__");
  const [summary, setSummary] = useState<ReportSummaryResponse | null>(null);
  const [backfillMsg, setBackfillMsg] = useState<string>("");
  const [backfillKind, setBackfillKind] = useState<"mt5" | "okx">("mt5");

  useEffect(() => {
    fetchReportsList().then((items) => {
      setReports(items);
      if (items.length > 0) setSelectedKey(items[0].key);
    });
  }, []);

  useEffect(() => {
    if (!selectedKey) return;
    fetchReportSummary(selectedKey, { strategy: strategy === "__all__" ? undefined : strategy }).then(setSummary);
  }, [selectedKey, strategy]);

  const strategies = useMemo(() => {
    // Strategy filter values come from `decision_stance` on the CSV rows;
    // discovering the actual set would need a dedicated endpoint, so this
    // stays a fixed list matching `GeneralSettings.decision_stance`'s enum
    // until a real "list distinct strategies" need shows up.
    return ["conservative", "balanced", "aggressive", "extreme_aggressive"];
  }, []);

  async function runBackfill() {
    if (!selectedKey) return;
    setBackfillMsg("回填中…");
    try {
      const result = await triggerBackfill(selectedKey, backfillKind);
      setBackfillMsg(`处理 ${result.processed} 笔，匹配 ${result.matched} 笔，未匹配 ${result.unmatched} 笔`);
      fetchReportSummary(selectedKey, { strategy: strategy === "__all__" ? undefined : strategy }).then(setSummary);
    } catch (err) {
      setBackfillMsg(`回填失败: ${(err as Error).message}`);
    }
  }

  if (nav !== "overview") {
    return (
      <div className="reports-shell">
        <SideNav active={nav} onSelect={setNav} />
        <main className="reports-main">
          <div className="reports-placeholder-page" data-testid="reports-placeholder">
            开发中
          </div>
        </main>
      </div>
    );
  }

  return (
    <div className="reports-shell">
      <SideNav active={nav} onSelect={setNav} />
      <main className="reports-main">
        <div className="reports-header">
          <div className="reports-title-block">
            <h1>交易记录分析报告</h1>
            <div className="reports-breadcrumb">账户表现 / 风险控制 / 交易质量 / 订单复盘</div>
          </div>
          <div className="reports-filters">
            <select value={selectedKey} onChange={(e) => setSelectedKey(e.target.value)}>
              {reports.length === 0 && <option value="">暂无交易记录文件</option>}
              {reports.map((r) => (
                <option key={r.key} value={r.key}>
                  {r.symbol} {r.timeframe} ({r.row_count})
                </option>
              ))}
            </select>
            <select value={strategy} onChange={(e) => setStrategy(e.target.value)}>
              <option value="__all__">全部策略</option>
              {strategies.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
            <select value={backfillKind} onChange={(e) => setBackfillKind(e.target.value as "mt5" | "okx")}>
              <option value="mt5">MT5</option>
              <option value="okx">OKX</option>
            </select>
            <button className="reports-manage-btn" onClick={runBackfill} disabled={!selectedKey}>
              回填真实成交
            </button>
          </div>
        </div>
        {backfillMsg && <p className="reports-kpi-sub">{backfillMsg}</p>}

        {!selectedKey && (
          <p className="reports-kpi-sub">
            trade_records/ 目录下还没有交易记录 CSV。请先在工作台完成一次分析后再回到本页面。
          </p>
        )}

        {summary && (
          <>
            <div className="reports-kpi-row">
              <KpiCard label="总收益" value={formatUsd(summary.total_pnl_usd)} />
              <KpiCard
                label="最大回撤"
                value={formatUsd(-summary.max_drawdown_usd)}
                subLabel={summary.max_drawdown_pct === null ? undefined : `占峰值 ${formatPct(summary.max_drawdown_pct * 100)}`}
              />
              <KpiCard
                label="盈利因子"
                value={summary.profit_factor === null ? "—" : summary.profit_factor.toFixed(2)}
              />
              <KpiCard
                label="胜率"
                value={formatPct(summary.win_rate_pct)}
                subLabel={`胜/负 ${summary.win_count} / ${summary.loss_count}`}
              />
              <KpiCard label="平均每笔比" value={formatRatio(summary.avg_win_loss_ratio)} subLabel="平均盈利/平均亏损" />
              <KpiCard
                label="交易次数"
                value={String(summary.trade_count)}
                subLabel={`日均交易 ${summary.avg_trades_per_day.toFixed(2)}`}
              />
              <KpiCard label="最大连续亏损" value={String(summary.max_consecutive_losses)} subLabel="当前筛选范围" />
              <KpiCard label="停滞天数" value={`${summary.stagnation_days} 天`} subLabel="最长修复，尚未恢复" />
            </div>

            <div className="reports-chart-grid">
              <EquityCurveChart data={summary.equity_curve} />
              <MonthlyReturnsChart data={summary.monthly_returns} />
              <SymbolDistributionChart data={summary.symbol_distribution} />
            </div>

            <div className="reports-chart-grid">
              <PnlCalendar reportKey={selectedKey} strategy={strategy === "__all__" ? undefined : strategy} />
              <TradeOverviewChart longNetPnl={summary.long_net_pnl_usd} shortNetPnl={summary.short_net_pnl_usd} />
              <DirectionAnalysisChart longWinRate={summary.long_win_rate_pct} shortWinRate={summary.short_win_rate_pct} />
            </div>

            <div className="reports-chart-grid">
              <PnlOverviewChart winCount={summary.win_count} lossCount={summary.loss_count} />
              <HoldingTimeChart data={summary.holding_time_distribution} />
              <SlippageChart data={summary.slippage} />
            </div>

            <OrderTable reportKey={selectedKey} filters={{ strategy: strategy === "__all__" ? undefined : strategy }} />
          </>
        )}
      </main>
    </div>
  );
}
