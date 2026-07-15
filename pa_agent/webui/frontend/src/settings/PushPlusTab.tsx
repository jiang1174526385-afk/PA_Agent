import { useEffect, useState } from "react";
import { fetchSettingsSection, saveSettingsSection } from "../api/paAgentApi";
import type { PushPlusRead } from "../types/domain";
import { SecretInput } from "./SecretInput";

export function PushPlusTab() {
  const [data, setData] = useState<PushPlusRead | null>(null);
  const [enabled, setEnabled] = useState(false);
  const [token, setToken] = useState<string | undefined>(undefined);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettingsSection("pushplus").then((d) => {
      setData(d);
      setEnabled(d.enabled);
    });
  }, []);

  if (!data) return <p className="placeholder">加载中…</p>;

  async function save() {
    setSaving(true);
    try {
      const updated = await saveSettingsSection("pushplus", { enabled, token });
      setData(updated);
      setToken(undefined);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="form-row">
        <label>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />{" "}
          启用 PushPlus 通知
        </label>
      </div>
      <SecretInput
        label="Token"
        maskedValue={data.token_masked}
        isSet={data.token_set}
        value={token}
        onChange={setToken}
      />
      <p className="placeholder">本阶段仅支持配置项 CRUD，不会实际触发通知发送。</p>
      <button onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
