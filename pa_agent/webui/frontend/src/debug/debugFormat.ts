// Pure display formatting for the AI debug panel -- mirrors
// pa_agent/gui/debug_widget.py::_format_raw_response / build_debug_bundle().

import type { ChatDebugTurn } from "../types/domain";

export function formatRawResponse(raw: Record<string, unknown>): string {
  if (!raw || Object.keys(raw).length === 0) return "";
  const usage = (raw.usage as Record<string, unknown>) || {};
  const promptTokens = Number(usage.prompt_tokens ?? 0);
  const cachedTokens = Number(usage.cached_prompt_tokens ?? 0);
  const missTokens = Number(usage.cache_miss_tokens ?? promptTokens - cachedTokens);
  const completionTokens = Number(usage.completion_tokens ?? 0);
  let hitPct = usage.cache_hit_rate_pct as number | undefined;

  let banner = "";
  if (promptTokens > 0) {
    if (hitPct == null) hitPct = (cachedTokens / promptTokens) * 100.0;
    banner =
      `═══ KV Cache ═══\n` +
      `  命中：${cachedTokens.toLocaleString()} tokens (${hitPct.toFixed(1)}%)  ` +
      `未命中：${missTokens.toLocaleString()} tokens\n` +
      `  输入合计：${promptTokens.toLocaleString()}  输出：${completionTokens.toLocaleString()}\n` +
      `═══════════════\n\n`;
  }
  return `${banner}${JSON.stringify(raw, null, 2)}`;
}

export function buildDebugBundle(turn: ChatDebugTurn): string {
  const parts: string[] = [`=== ${turn.label} ===`];
  if (turn.validation_info) {
    parts.push("\n--- Validation / Exception ---\n", turn.validation_info);
  }
  if (turn.raw_response && Object.keys(turn.raw_response).length > 0) {
    parts.push("\n--- Raw Response ---\n", formatRawResponse(turn.raw_response));
  }
  if (turn.system_prompt || turn.user_prompt) {
    parts.push("\n--- System Prompt ---\n", turn.system_prompt, "\n--- User Prompt ---\n", turn.user_prompt);
  }
  return parts.join("\n").trim();
}
