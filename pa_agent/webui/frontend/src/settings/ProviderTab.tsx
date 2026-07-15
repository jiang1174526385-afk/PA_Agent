import { useEffect, useState } from "react";
import { fetchModels, fetchSettingsSection, saveSettingsSection } from "../api/paAgentApi";
import type { ProviderRead } from "../types/domain";
import { SecretInput } from "./SecretInput";

export function ProviderTab() {
  const [data, setData] = useState<ProviderRead | null>(null);
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [apiKey, setApiKey] = useState<string | undefined>(undefined);
  const [thinking, setThinking] = useState(true);
  const [reasoningEffort, setReasoningEffort] =
    useState<ProviderRead["reasoning_effort"]>("high");
  const [contextWindow, setContextWindow] = useState(2_000_000);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettingsSection("provider").then((d) => {
      setData(d);
      setModel(d.model);
      setBaseUrl(d.base_url);
      setThinking(d.thinking);
      setReasoningEffort(d.reasoning_effort);
      setContextWindow(d.context_window);
    });
    fetchModels().then(setModels);
  }, []);

  if (!data) return <p className="placeholder">加载中…</p>;

  async function save() {
    setSaving(true);
    try {
      const updated = await saveSettingsSection("provider", {
        model,
        base_url: baseUrl,
        api_key: apiKey,
        thinking,
        reasoning_effort: reasoningEffort,
        context_window: contextWindow,
      });
      setData(updated);
      setApiKey(undefined);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="form-row">
        <label htmlFor="provider-model">模型</label>
        <input
          id="provider-model"
          list="model-options"
          value={model}
          onChange={(e) => setModel(e.target.value)}
        />
        <datalist id="model-options">
          {models.map((m) => (
            <option key={m} value={m} />
          ))}
        </datalist>
      </div>

      <div className="form-row">
        <label htmlFor="provider-base-url">Base URL</label>
        <input id="provider-base-url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)} />
      </div>

      <SecretInput
        label="API Key"
        maskedValue={data.api_key_masked}
        isSet={data.api_key_set}
        value={apiKey}
        onChange={setApiKey}
      />

      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={thinking}
            onChange={(e) => setThinking(e.target.checked)}
          />{" "}
          启用思维链 (thinking)
        </label>
      </div>

      <div className="form-row">
        <label htmlFor="provider-reasoning-effort">推理强度</label>
        <select
          id="provider-reasoning-effort"
          value={reasoningEffort}
          onChange={(e) => setReasoningEffort(e.target.value as ProviderRead["reasoning_effort"])}
        >
          <option value="low">low</option>
          <option value="medium">medium</option>
          <option value="high">high</option>
          <option value="max">max</option>
        </select>
      </div>

      <div className="form-row">
        <label htmlFor="provider-context-window">上下文窗口</label>
        <input
          id="provider-context-window"
          type="number"
          value={contextWindow}
          onChange={(e) => setContextWindow(Number(e.target.value))}
        />
      </div>

      <button onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
