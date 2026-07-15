import { useEffect, useState } from "react";
import { fetchSettingsSection, saveSettingsSection } from "../api/paAgentApi";
import type { GeneralRead } from "../types/domain";

type FieldConfig =
  | { key: keyof GeneralRead; label: string; kind: "number" }
  | { key: keyof GeneralRead; label: string; kind: "text" }
  | { key: keyof GeneralRead; label: string; kind: "boolean" }
  | { key: keyof GeneralRead; label: string; kind: "select"; options: string[] };

const FIELDS: FieldConfig[] = [
  { key: "analysis_bar_count", label: "分析K线数量", kind: "number" },
  { key: "refresh_interval_ms", label: "刷新间隔 (ms)", kind: "number" },
  { key: "context_warning_threshold_pct", label: "上下文警告阈值 (%)", kind: "number" },
  { key: "kline_adjust", label: "复权方式", kind: "select", options: ["qfq", "hfq", "none"] },
  { key: "last_tradingview_exchange", label: "TradingView 交易所", kind: "text" },
  { key: "last_symbol", label: "上次品种", kind: "text" },
  { key: "last_timeframe", label: "上次周期", kind: "text" },
  {
    key: "decision_stance",
    label: "决策倾向",
    kind: "select",
    options: ["conservative", "balanced", "aggressive", "extreme_aggressive"],
  },
  { key: "decision_confidence_threshold", label: "决策置信度阈值", kind: "number" },
  { key: "incremental_max_new_bars", label: "增量分析最大新增K线数", kind: "number" },
  { key: "structure_flip_cooldown_bars", label: "结构翻转冷却K线数", kind: "number" },
  { key: "decision_flow_auto_play", label: "流程图自动播放", kind: "boolean" },
  { key: "decision_flow_play_seconds", label: "流程图播放秒数", kind: "number" },
  { key: "decision_flow_default_zoom_pct", label: "流程图默认缩放 (%)", kind: "number" },
  { key: "alert_on_order_opportunity", label: "下单机会提醒", kind: "boolean" },
  { key: "enable_next_bar_prediction", label: "启用下一根K线预测", kind: "boolean" },
  { key: "auto_resume_chart_after_analysis", label: "分析后自动恢复图表刷新", kind: "boolean" },
  { key: "keep_analysis", label: "保留分析记录", kind: "boolean" },
  { key: "cancel_keep_analysis_on_retry", label: "重试时取消保留分析", kind: "boolean" },
  { key: "stream_pane_font_pt", label: "流式面板字号 (pt)", kind: "number" },
  { key: "chart_seq_label_font_pt", label: "图表序号字号 (pt)", kind: "number" },
];

export function GeneralTab() {
  const [data, setData] = useState<GeneralRead | null>(null);
  const [form, setForm] = useState<Record<string, unknown>>({});
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettingsSection("general").then((d) => {
      setData(d);
      setForm({ ...d });
    });
  }, []);

  if (!data) return <p className="placeholder">加载中…</p>;

  function setField(key: string, value: unknown) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  async function save() {
    setSaving(true);
    try {
      const updated = await saveSettingsSection("general", form);
      setData(updated);
      setForm({ ...updated });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      {FIELDS.map((field) => {
        const inputId = `general-${field.key}`;
        return (
          <div className="form-row" key={field.key}>
            <label htmlFor={inputId}>{field.label}</label>
            {field.kind === "boolean" ? (
              <input
                id={inputId}
                type="checkbox"
                checked={Boolean(form[field.key])}
                onChange={(e) => setField(field.key, e.target.checked)}
              />
            ) : field.kind === "select" ? (
              <select
                id={inputId}
                value={String(form[field.key] ?? "")}
                onChange={(e) => setField(field.key, e.target.value)}
              >
                {field.options.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            ) : field.kind === "number" ? (
              <input
                id={inputId}
                type="number"
                value={Number(form[field.key] ?? 0)}
                onChange={(e) => setField(field.key, Number(e.target.value))}
              />
            ) : (
              <input
                id={inputId}
                type="text"
                value={String(form[field.key] ?? "")}
                onChange={(e) => setField(field.key, e.target.value)}
              />
            )}
          </div>
        );
      })}
      <button onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
