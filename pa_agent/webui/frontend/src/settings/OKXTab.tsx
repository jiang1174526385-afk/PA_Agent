import { useEffect, useState } from "react";
import { fetchSettingsSection, saveSettingsSection } from "../api/paAgentApi";
import type { OKXRead } from "../types/domain";
import { SecretInput } from "./SecretInput";

export function OKXTab() {
  const [data, setData] = useState<OKXRead | null>(null);
  const [apiKey, setApiKey] = useState<string | undefined>(undefined);
  const [apiSecret, setApiSecret] = useState<string | undefined>(undefined);
  const [passphrase, setPassphrase] = useState<string | undefined>(undefined);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettingsSection("okx").then(setData);
  }, []);

  if (!data) return <p className="placeholder">加载中…</p>;

  async function save() {
    setSaving(true);
    try {
      const updated = await saveSettingsSection("okx", {
        api_key: apiKey,
        api_secret: apiSecret,
        passphrase,
      });
      setData(updated);
      setApiKey(undefined);
      setApiSecret(undefined);
      setPassphrase(undefined);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <p className="placeholder">
        仅用于交易记录分析报告页面回填真实历史成交（OKX 私有端点 /api/v5/account/positions-history），
        与现有 K线数据源（公共端点，无需鉴权）无关。
      </p>
      <SecretInput
        label="API Key"
        maskedValue={data.api_key_masked}
        isSet={data.api_key_set}
        value={apiKey}
        onChange={setApiKey}
      />
      <SecretInput
        label="API Secret"
        maskedValue={data.api_secret_masked}
        isSet={data.api_secret_set}
        value={apiSecret}
        onChange={setApiSecret}
      />
      <SecretInput
        label="Passphrase"
        maskedValue={data.passphrase_masked}
        isSet={data.passphrase_set}
        value={passphrase}
        onChange={setPassphrase}
      />
      <button onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
