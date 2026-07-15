import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { SlippageDistribution } from "../../types/domain";

export function SlippageChart({ data }: { data: SlippageDistribution }) {
  return (
    <div className="reports-card" data-testid="slippage-chart">
      <div className="reports-card-header">
        <span>执行质量 / 滑点分布</span>
        <span style={{ color: data.avg && data.avg >= 0 ? "#16a34a" : "#dc2626" }}>
          平均滑点 {data.avg === null ? "—" : `${data.avg >= 0 ? "+" : ""}${data.avg.toFixed(2)}`}
        </span>
      </div>
      {data.buckets.length === 0 || data.avg === null ? (
        <p className="reports-kpi-sub">暂无可计算滑点的已回填成交（缺少 entry_price）</p>
      ) : (
        <ResponsiveContainer width="100%" height={180}>
          <BarChart data={data.buckets}>
            <XAxis dataKey="label" tick={{ fontSize: 10 }} />
            <YAxis width={40} />
            <Tooltip />
            <Bar dataKey="count" fill="#d97706" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
