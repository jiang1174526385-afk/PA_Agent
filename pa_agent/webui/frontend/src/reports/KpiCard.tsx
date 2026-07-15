export function KpiCard({
  label,
  value,
  subLabel,
}: {
  label: string;
  value: string;
  subLabel?: string;
}) {
  return (
    <div className="reports-kpi-card">
      <div className="reports-kpi-label">{label}</div>
      <div className="reports-kpi-value">{value}</div>
      {subLabel && <div className="reports-kpi-sub">{subLabel}</div>}
    </div>
  );
}
