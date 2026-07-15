import { describe, expect, it } from "vitest";
import { formatDemoRecordLabel } from "./demoFormat";

describe("formatDemoRecordLabel", () => {
  it("combines symbol, timeframe, and a trimmed local timestamp", () => {
    const label = formatDemoRecordLabel({
      record_id: "a.json",
      symbol: "BTC-USDT-SWAP",
      timeframe: "15m",
      timestamp_local_iso: "2026-07-15T12:34:56.789",
    });
    expect(label).toBe("BTC-USDT-SWAP 15m · 2026-07-15 12:34:56");
  });

  it("tolerates a bare-seconds ISO string (no fractional part)", () => {
    const label = formatDemoRecordLabel({
      record_id: "b.json",
      symbol: "XAUUSDm",
      timeframe: "1h",
      timestamp_local_iso: "2026-01-01T00:00:00",
    });
    expect(label).toBe("XAUUSDm 1h · 2026-01-01 00:00:00");
  });
});
