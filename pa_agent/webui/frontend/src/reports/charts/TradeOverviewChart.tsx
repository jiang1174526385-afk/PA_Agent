import { formatUsd } from "../format";
import { DonutChart } from "./DonutChart";

export function TradeOverviewChart({
  longNetPnl,
  shortNetPnl,
}: {
  longNetPnl: number;
  shortNetPnl: number;
}) {
  const slices = [
    { name: "多头", value: Math.abs(longNetPnl), color: "#16a34a" },
    { name: "空头", value: Math.abs(shortNetPnl), color: "#dc2626" },
  ];
  return (
    <div className="reports-card" data-testid="trade-overview-chart">
      <div className="reports-card-header">
        <span>交易概览</span>
      </div>
      <DonutChart slices={slices} centerValue={formatUsd(longNetPnl + shortNetPnl)} centerLabel="净收益" />
      <div style={{ display: "flex", justifyContent: "space-around", fontSize: 12, marginTop: 8 }}>
        <span style={{ color: "#16a34a" }}>多头 {formatUsd(longNetPnl)}</span>
        <span style={{ color: "#dc2626" }}>空头 {formatUsd(shortNetPnl)}</span>
      </div>
    </div>
  );
}
