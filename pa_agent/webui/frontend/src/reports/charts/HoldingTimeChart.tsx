import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { HoldingTimeBucket } from "../../types/domain";

export function HoldingTimeChart({ data }: { data: HoldingTimeBucket[] }) {
  return (
    <div className="reports-card" data-testid="holding-time-chart">
      <div className="reports-card-header">
        <span>持仓时间分布</span>
      </div>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data}>
          <XAxis dataKey="bucket" tick={{ fontSize: 10 }} />
          <YAxis width={40} />
          <Tooltip
            formatter={(value, _name, props) => [
              `${value} 笔 (${(props.payload as HoldingTimeBucket).pct.toFixed(1)}%)`,
              "数量",
            ]}
          />
          <Bar dataKey="count" fill="#6d5bd0" />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
