export function formatUsd(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : value < 0 ? "-" : "";
  return `${sign}$${Math.abs(value).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatPct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

export function formatRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value.toFixed(2)} : 1`;
}

export function formatHoldingDuration(seconds: number | string | null | undefined): string {
  const s = typeof seconds === "string" ? parseFloat(seconds) : seconds;
  if (s === null || s === undefined || Number.isNaN(s)) return "—";
  if (s < 60) return `${Math.round(s)}秒`;
  if (s < 3600) return `${(s / 60).toFixed(1)}分钟`;
  if (s < 86400) return `${(s / 3600).toFixed(2)}小时`;
  return `${(s / 86400).toFixed(2)}天`;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toISOString().replace("T", " ").slice(0, 19) + " UTC";
}
