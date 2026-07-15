import type { DemoRecordSummary } from "../types/domain";

/** Label shown in the demo-record `<select>` (Toolbar.tsx). */
export function formatDemoRecordLabel(r: DemoRecordSummary): string {
  return `${r.symbol} ${r.timeframe} · ${r.timestamp_local_iso.slice(0, 19).replace("T", " ")}`;
}
