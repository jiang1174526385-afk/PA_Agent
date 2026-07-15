import { useState } from "react";
import type { AnalysisRecord } from "../types/domain";
import { turnSummary } from "./chatFormat";
import { useChatSession } from "./useChatSession";

interface ChatPanelProps {
  record: AnalysisRecord | null;
}

/** Free-chat panel: one shared input drives two read-only display views of
 * the same /ws/chat stream (per phase-5-execution-plan.md §0.3) --
 * "时间线" (ConversationWidget equivalent: turn summaries + click-to-expand
 * detail) and "原始流" (AiStreamWindow equivalent: continuous raw token log). */
export function ChatPanel({ record }: ChatPanelProps) {
  const session = useChatSession();
  const [view, setView] = useState<"timeline" | "raw">("timeline");
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [inputText, setInputText] = useState("");

  const inputEnabled = record !== null && !session.sending;
  const selectedTurn = session.turns.find((t) => t.id === selectedId) ?? null;

  function handleSend() {
    if (!inputText.trim()) return;
    session.send(inputText);
    setInputText("");
  }

  const tokenUsage = session.tokenUsage;
  const contextPct = tokenUsage ? Math.min(100, tokenUsage.context_pct) : 0;

  return (
    <div className="chat-panel panel" data-testid="chat-panel">
      <div className="chat-header">
        <span className="chat-title">自由对话</span>
        <div className="chat-view-toggle">
          <button
            type="button"
            className={view === "timeline" ? "chat-toggle-btn active" : "chat-toggle-btn"}
            onClick={() => setView("timeline")}
          >
            时间线
          </button>
          <button
            type="button"
            className={view === "raw" ? "chat-toggle-btn active" : "chat-toggle-btn"}
            onClick={() => setView("raw")}
          >
            原始流
          </button>
        </div>
      </div>

      {tokenUsage && (
        <div className="chat-token-bar">
          <span className="chat-token-label">上下文</span>
          <div className="chat-token-progress">
            <div className="chat-token-progress-fill" style={{ width: `${contextPct}%` }} />
          </div>
          <span className="chat-token-text">
            {tokenUsage.context_used.toLocaleString()} / {tokenUsage.context_window.toLocaleString()} ·{" "}
            {tokenUsage.context_pct.toFixed(1)}%
          </span>
        </div>
      )}

      {view === "timeline" ? (
        <div className="chat-timeline-body">
          <ul className="chat-timeline-list">
            {session.turns.length === 0 && (
              <li className="chat-timeline-empty">
                {record ? "分析完成，可继续追问" : "分析完成后可继续追问…"}
              </li>
            )}
            {session.turns.map((turn) => (
              <li
                key={turn.id}
                className={
                  turn.id === selectedId ? "chat-timeline-item selected" : "chat-timeline-item"
                }
                title={turnSummary(turn)}
                onClick={() => setSelectedId(turn.id)}
              >
                {turnSummary(turn)}
              </li>
            ))}
          </ul>
          <div className="chat-timeline-detail">
            {selectedTurn ? (
              selectedTurn.kind === "user" ? (
                <div className="chat-bubble chat-bubble-user">{selectedTurn.content}</div>
              ) : (
                <div className="chat-bubble chat-bubble-ai">
                  {selectedTurn.reasoning && (
                    <div className="chat-reasoning">{selectedTurn.reasoning}</div>
                  )}
                  {selectedTurn.content && <div className="chat-content">{selectedTurn.content}</div>}
                  {selectedTurn.errorMessage && (
                    <div className="chat-error">[错误] {selectedTurn.errorMessage}</div>
                  )}
                </div>
              )
            ) : (
              <div className="chat-timeline-placeholder">点击左侧条目查看详情</div>
            )}
          </div>
        </div>
      ) : (
        <div className="chat-raw-stream">
          <pre className="chat-raw-log" data-testid="chat-raw-log">
            {session.rawLog || "等待追问…"}
          </pre>
          <button type="button" className="chat-clear-btn" onClick={session.clearRawLog}>
            清空
          </button>
        </div>
      )}

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          data-testid="chat-input"
          placeholder={record ? "分析完成后可继续追问…" : "请先完成一次分析"}
          value={inputText}
          disabled={!inputEnabled}
          onChange={(e) => setInputText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
        />
        {session.sending ? (
          <button type="button" className="chat-stop-btn" onClick={session.cancel}>
            停止
          </button>
        ) : (
          <button type="button" className="chat-send-btn" disabled={!inputEnabled} onClick={handleSend}>
            发送
          </button>
        )}
      </div>
    </div>
  );
}
