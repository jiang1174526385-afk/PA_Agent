import type { StageDecision } from "../types/domain";

function fmtPrice(v: number | null | undefined): string {
  return typeof v === "number" ? v.toPrecision(5).replace(/\.?0+$/, "") : "—";
}

function scoreColor(score: number | undefined): string {
  if (typeof score !== "number") return "var(--fg-2)";
  if (score >= 70) return "var(--success)";
  if (score >= 50) return "var(--warning)";
  return "var(--danger)";
}

function directionColor(direction: string | undefined): string {
  return direction && direction.includes("多") ? "var(--success)" : "var(--danger)";
}

/** Mirrors pa_agent/gui/decision_panel.py::DecisionPanel field-for-field
 * (trend/cycle/phase chips, diagnosis confidence bar, order summary, prices,
 * reasoning) so the web workbench matches the desktop layout. */
export function DecisionPanel({ decision }: { decision: StageDecision | null }) {
  if (!decision) {
    return (
      <div className="panel">
        <h3>AI 交易决策</h3>
        <p className="placeholder">等待分析</p>
      </div>
    );
  }

  const orderType = decision.order_type ?? "不下单";
  const reasoning = decision.reasoning ?? decision.brief_reasoning ?? "";

  return (
    <div className="panel">
      <h3>AI 交易决策</h3>

      <div className="chip-row">
        {decision.direction && <span className="chip">趋势 {decision.direction}</span>}
        {decision.cycle_position && (
          <span className="chip">
            周期 {decision.cycle_position}
            {decision.alternative_cycle_position ? ` · 备选 ${decision.alternative_cycle_position}` : ""}
          </span>
        )}
        {decision.market_phase && (
          <span className="chip">
            阶段 {decision.market_phase === "stable" ? "稳定" : "过渡"}
            {decision.transition_risk ? ` · 风险 ${decision.transition_risk}` : ""}
          </span>
        )}
      </div>

      {typeof decision.diagnosis_confidence === "number" && (
        <div style={{ marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>市场判断置信度</div>
          <div
            style={{
              background: "var(--surface-2)",
              borderRadius: 4,
              height: 6,
              marginTop: 4,
              overflow: "hidden",
            }}
          >
            <div
              style={{
                width: `${decision.diagnosis_confidence}%`,
                height: "100%",
                background: scoreColor(decision.diagnosis_confidence),
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: scoreColor(decision.diagnosis_confidence) }}>
            {decision.diagnosis_confidence} / 100
          </div>
          {decision.diagnosis_confidence_reasoning && (
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
              {decision.diagnosis_confidence_reasoning}
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <strong>{orderType}</strong>
        {typeof decision.trade_confidence === "number" && (
          <span style={{ fontSize: 12, color: "var(--fg-2)" }}>
            置信度 {decision.trade_confidence} / 100
          </span>
        )}
      </div>
      {decision.order_direction && (
        <div style={{ color: directionColor(decision.order_direction), fontSize: 13 }}>
          方向 {decision.order_direction}
        </div>
      )}

      <div className="price-row">
        <span>入场 {fmtPrice(decision.entry_price)}</span>
        <span>TP1 {fmtPrice(decision.take_profit_price)}</span>
        <span>TP2 {fmtPrice(decision.take_profit_price_2)}</span>
        <span>止损 {fmtPrice(decision.stop_loss_price)}</span>
      </div>

      {decision.trade_confidence_reasoning && (
        <p style={{ fontSize: 12, color: "var(--fg-2)" }}>{decision.trade_confidence_reasoning}</p>
      )}

      <h3>分析理由</h3>
      <div className="reasoning-box">{reasoning || "—"}</div>
    </div>
  );
}
