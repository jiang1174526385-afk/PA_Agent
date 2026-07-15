import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { EquityPoint } from "../../types/domain";
import { formatUsd } from "../format";

export function EquityCurveChart({ data }: { data: EquityPoint[] }) {
  return (
    <div className="reports-card" data-testid="equity-curve-chart">
      <div className="reports-card-header">
        <span>净值曲线</span>
      </div>
      {data.length === 0 ? (
        <p className="reports-kpi-sub">暂无已回填成交数据</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <LineChart data={data}>
            <XAxis dataKey="ts" tick={false} />
            <YAxis width={70} tickFormatter={(v) => formatUsd(v)} />
            <Tooltip
              formatter={(value) => formatUsd(Number(value))}
              labelFormatter={(label) => new Date(label).toLocaleString()}
            />
            <Line type="monotone" dataKey="equity_usd" stroke="#6d5bd0" dot={false} strokeWidth={2} />
          </LineChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
