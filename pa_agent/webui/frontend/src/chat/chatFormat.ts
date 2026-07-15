// Pure display formatting for the free-chat timeline -- mirrors
// pa_agent/gui/conversation_widget.py::_one_line_summary /
// _TurnRecord.timeline_summary().

export function oneLineSummary(text: string, maxLen = 42): string {
  const collapsed = text.trim().replace(/[\r\n]+/g, " ").replace(/\s+/g, " ");
  if (!collapsed) return "";
  if (collapsed.length > maxLen) return collapsed.slice(0, maxLen - 1) + "…";
  return collapsed;
}

export interface ChatTurnLike {
  kind: "user" | "chat";
  status: "streaming" | "done" | "error";
  content: string;
  reasoning: string;
  errorMessage?: string;
  elapsedS?: number;
}

export function turnSummary(turn: ChatTurnLike): string {
  if (turn.kind === "user") {
    const excerpt = oneLineSummary(turn.content, 36);
    return excerpt ? `用户: ${excerpt}` : "用户";
  }
  if (turn.status === "streaming") {
    return "追问  ⟳";
  }
  if (turn.status === "error") {
    return `追问 ✗ ${oneLineSummary(turn.errorMessage ?? "", 36)}`;
  }
  const tail = turn.elapsedS != null ? `  ·${turn.elapsedS.toFixed(0)}s` : "";
  const excerpt = oneLineSummary(turn.content) || oneLineSummary(turn.reasoning);
  return excerpt ? `✓ 追问${tail} — ${excerpt}` : `✓ 追问${tail}`;
}
