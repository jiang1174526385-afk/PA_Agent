import { useEffect, useState } from "react";
import { fetchChatDebugContext } from "../api/paAgentApi";
import type { AnalysisRecord } from "../types/domain";

interface ValidationDialogProps {
  record: AnalysisRecord;
  onClose: () => void;
}

/** Web equivalent of pa_agent/gui/validation_debug_dialog.py, shown when a
 * record has `exception` set -- mirrors main_window.py's
 * `_prompt_debug_report_for_bug_fix(..., exc_info=exc_info)` branch: headline
 * from exception.type/category, body is the same "⚠ 异常" turn the debug
 * panel shows (see phase-5-execution-plan.md §4, validation_debug_dialog.py's
 * caller). */
export function ValidationDialog({ record, onClose }: ValidationDialogProps) {
  const [body, setBody] = useState("");

  useEffect(() => {
    let cancelled = false;
    fetchChatDebugContext(record).then((resp) => {
      if (cancelled) return;
      const excTurn = resp.turns.find((t) => t.label === "⚠ 异常");
      setBody(excTurn?.validation_info ?? "");
    });
    return () => {
      cancelled = true;
    };
  }, [record]);

  const exc = record.exception ?? {};
  const errType = String(exc.type ?? "error");
  const category = String(exc.category ?? "");
  const message = String(exc.message ?? "");
  const headline =
    errType === "provider_error" || category === "e" ? "API 积分不足" : `分析未通过（${errType}）`;
  const detail = category ? `${category}: ${message}` : message || errType;

  function handleCopy() {
    navigator.clipboard?.writeText(body);
  }

  return (
    <div className="validation-dialog-overlay" onClick={onClose}>
      <div className="validation-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="validation-dialog-title">分析校验失败</div>
        <div className="validation-dialog-summary">
          {headline}
          <br />
          已切换到调试面板，可对照 Raw Response / Validation。
          {detail && (
            <>
              <br />
              摘要：{detail}
            </>
          )}
        </div>
        <pre className="validation-dialog-body">{body}</pre>
        <div className="validation-dialog-actions">
          <button type="button" onClick={handleCopy}>
            复制全部
          </button>
          <button type="button" onClick={onClose}>
            关闭
          </button>
        </div>
      </div>
    </div>
  );
}
