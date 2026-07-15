import { useEffect, useState } from "react";
import { fetchSettingsSection, saveSettingsSection } from "../api/paAgentApi";
import type { FeishuRead } from "../types/domain";
import { SecretInput } from "./SecretInput";

export function FeishuTab() {
  const [data, setData] = useState<FeishuRead | null>(null);
  const [enabled, setEnabled] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [secret, setSecret] = useState<string | undefined>(undefined);
  const [appId, setAppId] = useState("");
  const [appSecret, setAppSecret] = useState<string | undefined>(undefined);
  const [notifyOnOrderOnly, setNotifyOnOrderOnly] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSettingsSection("feishu").then((d) => {
      setData(d);
      setEnabled(d.enabled);
      setWebhookUrl(d.webhook_url);
      setAppId(d.app_id);
      setNotifyOnOrderOnly(d.notify_on_order_only);
    });
  }, []);

  if (!data) return <p className="placeholder">加载中…</p>;

  async function save() {
    setSaving(true);
    try {
      const updated = await saveSettingsSection("feishu", {
        enabled,
        webhook_url: webhookUrl,
        secret,
        app_id: appId,
        app_secret: appSecret,
        notify_on_order_only: notifyOnOrderOnly,
      });
      setData(updated);
      setSecret(undefined);
      setAppSecret(undefined);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <div className="form-row">
        <label>
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />{" "}
          启用飞书通知
        </label>
      </div>
      <div className="form-row">
        <label htmlFor="feishu-webhook-url">Webhook URL</label>
        <input
          id="feishu-webhook-url"
          value={webhookUrl}
          onChange={(e) => setWebhookUrl(e.target.value)}
        />
      </div>
      <SecretInput
        label="Secret"
        maskedValue={data.secret_masked}
        isSet={data.secret_set}
        value={secret}
        onChange={setSecret}
      />
      <div className="form-row">
        <label htmlFor="feishu-app-id">App ID</label>
        <input id="feishu-app-id" value={appId} onChange={(e) => setAppId(e.target.value)} />
      </div>
      <SecretInput
        label="App Secret"
        maskedValue={data.app_secret_masked}
        isSet={data.app_secret_set}
        value={appSecret}
        onChange={setAppSecret}
      />
      <div className="form-row">
        <label>
          <input
            type="checkbox"
            checked={notifyOnOrderOnly}
            onChange={(e) => setNotifyOnOrderOnly(e.target.checked)}
          />{" "}
          仅下单机会时通知
        </label>
      </div>
      <p className="placeholder">本阶段仅支持配置项 CRUD，不会实际触发通知发送。</p>
      <button onClick={save} disabled={saving}>
        {saving ? "保存中…" : "保存"}
      </button>
    </div>
  );
}
