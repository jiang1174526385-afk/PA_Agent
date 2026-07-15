import type { SymbolDistributionSlice } from "../../types/domain";
import { formatUsd } from "../format";
import { DonutChart } from "./DonutChart";

const PALETTE = ["#6d5bd0", "#8b7ae8", "#b3a4f5", "#dad2fb"];

export function SymbolDistributionChart({ data }: { data: SymbolDistributionSlice[] }) {
  const totalAbs = data.reduce((s, d) => s + d.abs_pnl_usd, 0);
  return (
    <div className="reports-card" data-testid="symbol-distribution-chart">
      <div className="reports-card-header">
        <span>品种分布</span>
      </div>
      {data.length === 0 ? (
        <p className="reports-kpi-sub">暂无数据</p>
      ) : (
        <>
          <DonutChart
            slices={data.map((d, i) => ({ name: d.symbol, value: d.abs_pnl_usd, color: PALETTE[i % PALETTE.length] }))}
            centerValue={formatUsd(totalAbs)}
            centerLabel="总收益(绝对值)"
          />
          <ul style={{ fontSize: 12, marginTop: 8, padding: 0, listStyle: "none" }}>
            {data.map((d, i) => (
              <li key={d.symbol} style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: PALETTE[i % PALETTE.length] }}>● {d.symbol}</span>
                <span>{d.pct.toFixed(1)}%</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}
