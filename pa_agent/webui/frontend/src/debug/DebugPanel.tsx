import { useEffect, useState } from "react";
import { fetchChatDebugContext } from "../api/paAgentApi";
import type { AnalysisRecord, ChatDebugTurn, PromptFilesInfo } from "../types/domain";
import { buildDebugBundle, formatRawResponse } from "./debugFormat";

interface DebugPanelProps {
  record: AnalysisRecord | null;
}

/** AI debug panel -- Web equivalent of pa_agent/gui/debug_widget.py.
 * Only Stage1/Stage2/exception turns are shown (follow-up chat turns are
 * never added to the desktop debug tab either, see
 * phase-5-execution-plan.md §4). Also renders the prompt-files panel
 * (pa_agent/gui/prompt_files_panel.py) since both derive from the same
 * `/api/chat/debug-context` call keyed on the current record. */
export function DebugPanel({ record }: DebugPanelProps) {
  const [turns, setTurns] = useState<ChatDebugTurn[]>([]);
  const [promptFiles, setPromptFiles] = useState<PromptFilesInfo | null>(null);
  const [selected, setSelected] = useState(0);
  const [copyStatus, setCopyStatus] = useState("");

  useEffect(() => {
    if (!record) {
      setTurns([]);
      setPromptFiles(null);
      return;
    }
    let cancelled = false;
    fetchChatDebugContext(record).then((resp) => {
      if (cancelled) return;
      setTurns(resp.turns);
      setPromptFiles(resp.prompt_files);
      setSelected(resp.turns.length - 1);
    });
    return () => {
      cancelled = true;
    };
  }, [record]);

  const turn = turns[selected] ?? null;

  function handleCopyDebugInfo() {
    if (!turn) return;
    const text = buildDebugBundle(turn);
    navigator.clipboard?.writeText(text).then(() => {
      setCopyStatus("已复制");
      setTimeout(() => setCopyStatus(""), 2000);
    });
  }

  return (
    <div className="debug-panel panel" data-testid="debug-panel">
      <div className="debug-header">调试面板</div>
      <div className="debug-body">
        <ul className="debug-turn-list">
          {turns.length === 0 && <li className="debug-turn-empty">尚无调试数据</li>}
          {turns.map((t, i) => (
            <li
              key={i}
              className={i === selected ? "debug-turn-item selected" : "debug-turn-item"}
              onClick={() => setSelected(i)}
            >
              {t.label}
            </li>
          ))}
        </ul>
        <div className="debug-detail">
          <div className="debug-field">
            <div className="debug-field-label">System Prompt</div>
            <pre className="debug-field-value">{turn?.system_prompt ?? ""}</pre>
          </div>
          <div className="debug-field">
            <div className="debug-field-label">User Prompt</div>
            <pre className="debug-field-value">{turn?.user_prompt ?? ""}</pre>
          </div>
          <div className="debug-field">
            <div className="debug-field-label">Raw Response</div>
            <pre className="debug-field-value">{turn ? formatRawResponse(turn.raw_response) : ""}</pre>
          </div>
          <div className="debug-field">
            <div className="debug-field-label">Validation / Exception</div>
            <pre className="debug-field-value">{turn?.validation_info ?? ""}</pre>
          </div>
          <div className="debug-actions">
            <button type="button" disabled={!turn} onClick={handleCopyDebugInfo}>
              复制调试信息
            </button>
            {copyStatus && <span className="debug-copy-status">{copyStatus}</span>}
          </div>
        </div>
      </div>

      <div className="prompt-files-panel" data-testid="prompt-files-panel">
        <div className="prompt-files-hint">本次分析注入到 system 提示词中的 .txt 文件（按发送顺序）</div>
        <div className="prompt-files-columns">
          <div>
            <div className="prompt-files-title stage1">阶段一 · 市场诊断</div>
            <ul className="prompt-files-list">
              {(promptFiles?.stage1_files.length ?? 0) === 0 ? (
                <li className="prompt-files-empty">（尚未开始阶段一）</li>
              ) : (
                promptFiles!.stage1_files.map((f, i) => <li key={i}>{`${i + 1}. ${f}`}</li>)
              )}
            </ul>
          </div>
          <div>
            <div className="prompt-files-title stage2">阶段二 · 交易决策</div>
            <ul className="prompt-files-list">
              {(promptFiles?.stage2_files.length ?? 0) === 0 ? (
                <li className="prompt-files-empty">（阶段二尚未开始）</li>
              ) : (
                promptFiles!.stage2_files.map((f, i) => <li key={i}>{`${i + 1}. ${f}`}</li>)
              )}
            </ul>
          </div>
        </div>
        {promptFiles && (
          <div className="prompt-files-extra">
            {[
              promptFiles.stage1_builtin && "阶段一另含内置 JSON 输出格式说明（非 txt）",
              promptFiles.stage2_builtin && "阶段二另含内置 JSON 决策契约（非 txt）",
              promptFiles.experience_count > 0 && `阶段二另注入经验库 ${promptFiles.experience_count} 条（非 txt）`,
            ]
              .filter(Boolean)
              .join(" · ")}
          </div>
        )}
      </div>
    </div>
  );
}
