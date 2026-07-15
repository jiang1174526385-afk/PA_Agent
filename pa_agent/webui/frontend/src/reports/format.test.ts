import { describe, expect, it } from "vitest";
import { formatDateTime, formatHoldingDuration, formatPct, formatRatio, formatUsd } from "./format";

describe("formatUsd", () => {
  it("formats positive with sign", () => {
    expect(formatUsd(162334.1)).toBe("+$162,334.10");
  });
  it("formats negative", () => {
    expect(formatUsd(-10772.1)).toBe("-$10,772.10");
  });
  it("handles null/NaN", () => {
    expect(formatUsd(null)).toBe("—");
    expect(formatUsd(NaN)).toBe("—");
  });
});

describe("formatPct", () => {
  it("formats with 2 digits by default", () => {
    expect(formatPct(67.034)).toBe("67.03%");
  });
  it("handles null", () => {
    expect(formatPct(null)).toBe("—");
  });
});

describe("formatRatio", () => {
  it("formats as X : 1", () => {
    expect(formatRatio(0.99)).toBe("0.99 : 1");
  });
  it("handles null", () => {
    expect(formatRatio(null)).toBe("—");
  });
});

describe("formatHoldingDuration", () => {
  it("formats minutes", () => {
    expect(formatHoldingDuration(900)).toBe("15.0分钟");
  });
  it("formats hours", () => {
    expect(formatHoldingDuration(7200)).toBe("2.00小时");
  });
  it("formats seconds under a minute", () => {
    expect(formatHoldingDuration(30)).toBe("30秒");
  });
  it("handles null", () => {
    expect(formatHoldingDuration(null)).toBe("—");
  });
});

describe("formatDateTime", () => {
  it("formats ISO string", () => {
    expect(formatDateTime("2026-06-30T00:56:31+00:00")).toBe("2026-06-30 00:56:31 UTC");
  });
  it("handles empty", () => {
    expect(formatDateTime("")).toBe("—");
  });
});
