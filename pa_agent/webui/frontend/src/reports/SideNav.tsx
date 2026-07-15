export type ReportsNavKey = "overview" | "compare" | "returns" | "risk" | "strategy" | "settings";

const ITEMS: { key: ReportsNavKey; icon: string; label: string }[] = [
  { key: "overview", icon: "🏠", label: "总览" },
  { key: "compare", icon: "📑", label: "报告对比" },
  { key: "returns", icon: "📈", label: "收益分析" },
  { key: "risk", icon: "🛡", label: "风险分析" },
  { key: "strategy", icon: "🧭", label: "策略分析" },
  { key: "settings", icon: "⚙", label: "设置" },
];

export function SideNav({
  active,
  onSelect,
}: {
  active: ReportsNavKey;
  onSelect: (key: ReportsNavKey) => void;
}) {
  return (
    <nav className="reports-sidenav" data-testid="reports-sidenav">
      {ITEMS.map((item) => (
        <button
          key={item.key}
          className={`reports-sidenav-item${item.key === active ? " active" : ""}`}
          onClick={() => onSelect(item.key)}
        >
          <span className="reports-sidenav-icon">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
      {/* Account card: no real account-identity data source exists anywhere in
          this project yet (no login/session concept) -- static placeholder
          until a real one is introduced, per phase-2 completion report. */}
      <div className="reports-sidenav-account">
        <div className="reports-sidenav-avatar">T</div>
        <div>交易员01</div>
        <div>专业账户</div>
      </div>
    </nav>
  );
}
