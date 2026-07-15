import { describe, expect, it } from "vitest";
import type { ChatDebugTurn } from "../types/domain";
import { buildDebugBundle, formatRawResponse } from "./debugFormat";

describe("formatRawResponse", () => {
  it("returns an empty string for an empty raw response", () => {
    expect(formatRawResponse({})).toBe("");
  });

  it("prepends a KV-cache banner when prompt_tokens is present", () => {
    const text = formatRawResponse({
      usage: { prompt_tokens: 100, cached_prompt_tokens: 80, completion_tokens: 20 },
    });
    expect(text).toContain("KV Cache");
    expect(text).toContain("命中：80 tokens (80.0%)");
    expect(text).toContain("未命中：20 tokens");
  });

  it("skips the banner when there are no prompt tokens", () => {
    const text = formatRawResponse({ id: "r1" });
    expect(text).not.toContain("KV Cache");
    expect(text).toContain('"id": "r1"');
  });
});

describe("buildDebugBundle", () => {
  const turn: ChatDebugTurn = {
    label: "Stage1 诊断",
    system_prompt: "system-text",
    user_prompt: "user-text",
    raw_response: { id: "r1" },
    validation_info: "校验通过",
  };

  it("includes the label, validation info, raw response, and prompts in order", () => {
    const bundle = buildDebugBundle(turn);
    const validationIdx = bundle.indexOf("校验通过");
    const rawIdx = bundle.indexOf('"id": "r1"');
    const systemIdx = bundle.indexOf("system-text");
    expect(bundle.startsWith("=== Stage1 诊断 ===")).toBe(true);
    expect(validationIdx).toBeGreaterThan(-1);
    expect(rawIdx).toBeGreaterThan(validationIdx);
    expect(systemIdx).toBeGreaterThan(rawIdx);
  });

  it("omits empty sections", () => {
    const bundle = buildDebugBundle({ ...turn, raw_response: {}, validation_info: "" });
    expect(bundle).not.toContain("Raw Response");
    expect(bundle).not.toContain("Validation");
  });
});
