import { describe, expect, it } from "vitest";
import { oneLineSummary, turnSummary } from "./chatFormat";

describe("oneLineSummary", () => {
  it("collapses newlines/whitespace and trims", () => {
    expect(oneLineSummary("  hello\nworld   foo  ")).toBe("hello world foo");
  });

  it("truncates with an ellipsis past maxLen", () => {
    const text = "a".repeat(50);
    const result = oneLineSummary(text, 10);
    expect(result).toHaveLength(10);
    expect(result.endsWith("…")).toBe(true);
  });

  it("returns empty string for blank input", () => {
    expect(oneLineSummary("   \n  ")).toBe("");
  });
});

describe("turnSummary", () => {
  it("prefixes user turns with 用户:", () => {
    expect(turnSummary({ kind: "user", status: "done", content: "止损应该设多少？", reasoning: "" })).toBe(
      "用户: 止损应该设多少？",
    );
  });

  it("shows a streaming spinner for in-flight chat turns", () => {
    expect(turnSummary({ kind: "chat", status: "streaming", content: "", reasoning: "" })).toBe("追问  ⟳");
  });

  it("shows elapsed time + excerpt for completed chat turns", () => {
    const summary = turnSummary({
      kind: "chat",
      status: "done",
      content: "建议维持当前止损位不变",
      reasoning: "",
      elapsedS: 3.4,
    });
    expect(summary).toBe("✓ 追问  ·3s — 建议维持当前止损位不变");
  });

  it("marks failed turns with the error excerpt", () => {
    const summary = turnSummary({
      kind: "chat",
      status: "error",
      content: "",
      reasoning: "",
      errorMessage: "API 积分不足",
    });
    expect(summary).toBe("追问 ✗ API 积分不足");
  });
});
