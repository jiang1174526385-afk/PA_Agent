import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

export interface DonutSlice {
  name: string;
  value: number;
  color: string;
}

/** Shared donut-chart primitive used by symbol distribution / trade overview /
 * direction analysis / P&L overview -- all four are "labelled ring" charts in
 * the design, differing only in slice data and the centre caption. */
export function DonutChart({
  slices,
  centerLabel,
  centerValue,
  size = 140,
}: {
  slices: DonutSlice[];
  centerLabel?: string;
  centerValue?: string;
  size?: number;
}) {
  const total = slices.reduce((sum, s) => sum + s.value, 0);
  return (
    <div style={{ position: "relative", width: size, height: size, margin: "0 auto" }}>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={slices}
            dataKey="value"
            innerRadius="65%"
            outerRadius="100%"
            paddingAngle={total > 0 ? 2 : 0}
            stroke="none"
          >
            {slices.map((s, i) => (
              <Cell key={i} fill={s.color} />
            ))}
          </Pie>
          <Tooltip />
        </PieChart>
      </ResponsiveContainer>
      {(centerLabel || centerValue) && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            pointerEvents: "none",
          }}
        >
          {centerValue && <div style={{ fontWeight: 700, fontSize: 15 }}>{centerValue}</div>}
          {centerLabel && (
            <div style={{ fontSize: 11, color: "var(--report-fg-muted)" }}>{centerLabel}</div>
          )}
        </div>
      )}
    </div>
  );
}
