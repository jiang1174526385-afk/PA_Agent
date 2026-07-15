import { useState } from "react";
import { FeishuTab } from "./FeishuTab";
import { GeneralTab } from "./GeneralTab";
import { ProviderTab } from "./ProviderTab";
import { PushPlusTab } from "./PushPlusTab";

type TabKey = "provider" | "general" | "feishu" | "pushplus";

const TABS: { key: TabKey; label: string }[] = [
  { key: "provider", label: "AI 模型" },
  { key: "general", label: "通用" },
  { key: "feishu", label: "飞书" },
  { key: "pushplus", label: "PushPlus" },
];

export function SettingsModal({ onClose }: { onClose: () => void }) {
  const [tab, setTab] = useState<TabKey>("provider");

  return (
    <div className="modal-overlay" onClick={onClose} data-testid="settings-modal">
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <strong>设置</strong>
          <button onClick={onClose}>✕</button>
        </div>
        <div className="modal-tabs">
          {TABS.map((t) => (
            <button
              key={t.key}
              className={t.key === tab ? "active" : ""}
              onClick={() => setTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="modal-body">
          {tab === "provider" && <ProviderTab />}
          {tab === "general" && <GeneralTab />}
          {tab === "feishu" && <FeishuTab />}
          {tab === "pushplus" && <PushPlusTab />}
        </div>
      </div>
    </div>
  );
}
