import { useCallback, useRef, useState } from "react";
import { useChatSocket } from "../api/paAgentWs";
import type { ChatTokenUsage, ChatWsInbound } from "../types/domain";

export interface ChatTurn {
  id: number;
  kind: "user" | "chat";
  status: "streaming" | "done" | "error";
  content: string;
  reasoning: string;
  errorMessage?: string;
  elapsedS?: number;
}

export interface ChatSessionApi {
  connected: boolean;
  sending: boolean;
  turns: ChatTurn[];
  rawLog: string;
  tokenUsage: ChatTokenUsage | null;
  send: (text: string) => void;
  cancel: () => void;
  clearRawLog: () => void;
}

let nextTurnId = 1;

/** Shared "engine" behind the two read-only display views (timeline +
 * raw stream console, mirroring ConversationWidget / AiStreamWindow) and the
 * single unified send box, per phase-5-execution-plan.md §0.3: one send
 * action drives both views off the same /ws/chat stream. */
export function useChatSession(): ChatSessionApi {
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [rawLog, setRawLog] = useState("");
  const [tokenUsage, setTokenUsage] = useState<ChatTokenUsage | null>(null);
  const [sending, setSending] = useState(false);
  const activeTurnId = useRef<number | null>(null);
  const activeStartMs = useRef(0);

  const onMessage = useCallback((msg: ChatWsInbound) => {
    if (msg.type === "chat_reasoning" || msg.type === "chat_content") {
      const id = activeTurnId.current;
      setRawLog((prev) => prev + msg.chunk);
      if (id == null) return;
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? {
                ...t,
                reasoning: msg.type === "chat_reasoning" ? t.reasoning + msg.chunk : t.reasoning,
                content: msg.type === "chat_content" ? t.content + msg.chunk : t.content,
              }
            : t,
        ),
      );
      return;
    }

    if (msg.type === "chat_done") {
      const id = activeTurnId.current;
      const elapsedS = (Date.now() - activeStartMs.current) / 1000;
      setTurns((prev) =>
        prev.map((t) =>
          t.id === id
            ? {
                ...t,
                status: "done",
                content: t.content || msg.content,
                reasoning: t.reasoning || msg.reasoning,
                elapsedS,
              }
            : t,
        ),
      );
      if (msg.token_usage) setTokenUsage(msg.token_usage);
      activeTurnId.current = null;
      setSending(false);
      return;
    }

    if (msg.type === "chat_error") {
      const id = activeTurnId.current;
      if (id != null) {
        setTurns((prev) =>
          prev.map((t) => (t.id === id ? { ...t, status: "error", errorMessage: msg.message } : t)),
        );
      } else {
        // No in-flight turn (e.g. "尚无可继续追问的分析结果" before any send).
        setTurns((prev) => [
          ...prev,
          {
            id: nextTurnId++,
            kind: "chat",
            status: "error",
            content: "",
            reasoning: "",
            errorMessage: msg.message,
          },
        ]);
      }
      activeTurnId.current = null;
      setSending(false);
      return;
    }
  }, []);

  const socket = useChatSocket(onMessage);

  const send = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) return;
      const userId = nextTurnId++;
      const chatId = nextTurnId++;
      activeTurnId.current = chatId;
      activeStartMs.current = Date.now();
      setTurns((prev) => [
        ...prev,
        { id: userId, kind: "user", status: "done", content: trimmed, reasoning: "" },
        { id: chatId, kind: "chat", status: "streaming", content: "", reasoning: "" },
      ]);
      setSending(true);
      socket.send(trimmed);
    },
    [socket],
  );

  const cancel = useCallback(() => socket.cancel(), [socket]);
  const clearRawLog = useCallback(() => setRawLog(""), []);

  return {
    connected: socket.connected,
    sending,
    turns,
    rawLog,
    tokenUsage,
    send,
    cancel,
    clearRawLog,
  };
}
