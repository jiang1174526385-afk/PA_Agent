import { DonutChart } from "./DonutChart";

export function PnlOverviewChart({ winCount, lossCount }: { winCount: number; lossCount: number }) {
  const total = winCount + lossCount;
  return (
    <div className="reports-card" data-testid="pnl-overview-chart">
      <div className="reports-card-header">
        <span>盈亏概览</span>
      </div>
      <DonutChart
        slices={[
          { name: "盈利", value: winCount, color: "#16a34a" },
          { name: "亏损", value: lossCount, color: "#dc2626" },
        ]}
        centerValue={String(total)}
        centerLabel="已匹配笔单入场"
      />
      <div style={{ display: "flex", justifyContent: "space-around", fontSize: 12, marginTop: 8 }}>
        <span style={{ color: "#16a34a" }}>盈利 {winCount} 笔</span>
        <span style={{ color: "#dc2626" }}>亏损 {lossCount} 笔</span>
      </div>
    </div>
  );
}
