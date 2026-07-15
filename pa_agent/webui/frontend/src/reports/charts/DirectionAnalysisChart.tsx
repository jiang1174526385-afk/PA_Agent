import { formatPct } from "../format";
import { DonutChart } from "./DonutChart";

export function DirectionAnalysisChart({
  longWinRate,
  shortWinRate,
}: {
  longWinRate: number | null;
  shortWinRate: number | null;
}) {
  return (
    <div className="reports-card" data-testid="direction-analysis-chart">
      <div className="reports-card-header">
        <span>交易方向分析（胜率）</span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-around" }}>
        <div style={{ textAlign: "center" }}>
          <DonutChart
            size={100}
            slices={[
              { name: "胜", value: longWinRate ?? 0, color: "#16a34a" },
              { name: "负", value: 100 - (longWinRate ?? 0), color: "#e6e9f2" },
            ]}
            centerValue={formatPct(longWinRate)}
          />
          <div style={{ fontSize: 12, marginTop: 4 }}>多头胜率</div>
        </div>
        <div style={{ textAlign: "center" }}>
          <DonutChart
            size={100}
            slices={[
              { name: "胜", value: shortWinRate ?? 0, color: "#16a34a" },
              { name: "负", value: 100 - (shortWinRate ?? 0), color: "#e6e9f2" },
            ]}
            centerValue={formatPct(shortWinRate)}
          />
          <div style={{ fontSize: 12, marginTop: 4 }}>空头胜率</div>
        </div>
      </div>
    </div>
  );
}
