import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { MonthlyReturnPoint } from "../../types/domain";
import { formatUsd } from "../format";

export function MonthlyReturnsChart({ data }: { data: MonthlyReturnPoint[] }) {
  return (
    <div className="reports-card" data-testid="monthly-returns-chart">
      <div className="reports-card-header">
        <span>月度收益 (USD)</span>
      </div>
      {data.length === 0 ? (
        <p className="reports-kpi-sub">暂无数据</p>
      ) : (
        <ResponsiveContainer width="100%" height={220}>
          <BarChart data={data}>
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis width={60} tickFormatter={(v) => formatUsd(v)} />
            <Tooltip formatter={(value) => formatUsd(Number(value))} />
            <Bar dataKey="pnl_usd">
              {data.map((d, i) => (
                <Cell key={i} fill={d.pnl_usd >= 0 ? "#16a34a" : "#dc2626"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
