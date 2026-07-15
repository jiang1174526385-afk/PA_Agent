import type { MaybeNestedStageDecision, StageDecision, TradeMetrics } from "../types/domain";

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

function fmtWinRate(v: number | null | undefined): string {
  return typeof v === "number" ? `${v}%` : "—";
}

function traderEquationColor(passed: boolean | null | undefined): string {
  if (passed === true) return "var(--success)";
  if (passed === false) return "var(--danger)";
  return "var(--fg-2)";
}

function traderEquationLabel(passed: boolean | null | undefined): string {
  if (passed === true) return "通过";
  if (passed === false) return "未通过";
  return "—";
}

/** Mirrors pa_agent/gui/decision_panel.py::DecisionPanel field-for-field
 * (trend/cycle/phase chips, diagnosis confidence bar, order summary, prices,
 * reasoning) so the web workbench matches the desktop layout. */
export function DecisionPanel({
  decision,
  tradeMetrics,
}: {
  decision: StageDecision | null;
  tradeMetrics?: TradeMetrics | null;
}) {
  if (!decision) {
    return (
      <div className="panel">
        <h3>AI 交易决策</h3>
        <p className="placeholder">等待分析</p>
      </div>
    );
  }

  // Phase 7 (§0.1): real production `stage2_decision` nests fields under a
  // `decision` key; historical test fixtures are flat. Normalize once here so
  // every field read below goes through `inner`, not the raw `decision` prop.
  const inner = (decision as MaybeNestedStageDecision)?.decision ?? decision;

  const orderType = inner.order_type ?? "不下单";
  const reasoning = inner.reasoning ?? inner.brief_reasoning ?? "";

  return (
    <div className="panel">
      <h3>AI 交易决策</h3>

      <div className="chip-row">
        {inner.direction && <span className="chip">趋势 {inner.direction}</span>}
        {inner.cycle_position && (
          <span className="chip">
            周期 {inner.cycle_position}
            {inner.alternative_cycle_position ? ` · 备选 ${inner.alternative_cycle_position}` : ""}
          </span>
        )}
        {inner.market_phase && (
          <span className="chip">
            阶段 {inner.market_phase === "stable" ? "稳定" : "过渡"}
            {inner.transition_risk ? ` · 风险 ${inner.transition_risk}` : ""}
          </span>
        )}
      </div>

      {typeof inner.diagnosis_confidence === "number" && (
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
                width: `${inner.diagnosis_confidence}%`,
                height: "100%",
                background: scoreColor(inner.diagnosis_confidence),
              }}
            />
          </div>
          <div style={{ fontSize: 12, color: scoreColor(inner.diagnosis_confidence) }}>
            {inner.diagnosis_confidence} / 100
          </div>
          {inner.diagnosis_confidence_reasoning && (
            <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
              {inner.diagnosis_confidence_reasoning}
            </div>
          )}
        </div>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
        <strong>{orderType}</strong>
        {typeof inner.trade_confidence === "number" && (
          <span style={{ fontSize: 12, color: "var(--fg-2)" }}>
            置信度 {inner.trade_confidence} / 100
          </span>
        )}
      </div>
      {inner.order_direction && (
        <div style={{ color: directionColor(inner.order_direction), fontSize: 13 }}>
          方向 {inner.order_direction}
        </div>
      )}

      <div className="price-row">
        <span>入场 {fmtPrice(inner.entry_price)}</span>
        <span>TP1 {fmtPrice(inner.take_profit_price)}</span>
        <span>TP2 {fmtPrice(inner.take_profit_price_2)}</span>
        <span>止损 {fmtPrice(inner.stop_loss_price)}</span>
      </div>

      {inner.trade_confidence_reasoning && (
        <p style={{ fontSize: 12, color: "var(--fg-2)" }}>{inner.trade_confidence_reasoning}</p>
      )}

      {tradeMetrics && (
        <div style={{ marginTop: 8, marginBottom: 8 }}>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
            风险回报比 <strong>{tradeMetrics.risk_reward_text ?? "—"}</strong>
          </div>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
            预估胜率 <strong>{fmtWinRate(tradeMetrics.estimated_win_rate_pct)}</strong>
          </div>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>
            交易者方程{" "}
            <strong style={{ color: traderEquationColor(tradeMetrics.trader_equation_passed) }}>
              {traderEquationLabel(tradeMetrics.trader_equation_passed)}
            </strong>
          </div>
        </div>
      )}

      <h3>分析理由</h3>
      <div className="reasoning-box">{reasoning || "—"}</div>
    </div>
  );
}
