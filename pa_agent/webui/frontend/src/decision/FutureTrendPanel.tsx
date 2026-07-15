import type { StageDecision } from "../types/domain";

const DIRECTION_ZH: Record<string, string> = { bullish: "阳线", bearish: "阴线", neutral: "中性" };
const DOMINANT_COLOR: Record<string, string> = {
  bullish: "var(--success)",
  bearish: "var(--danger)",
  neutral: "var(--warning)",
};

function dominantDirection(probs: { bullish: number; bearish: number; neutral: number }): string {
  const entries = Object.entries(probs) as [string, number][];
  entries.sort((a, b) => b[1] - a[1]);
  return entries[0][0];
}

/** Mirrors pa_agent/gui/future_trend_panel.py::FutureTrendPanel: next-bar and
 * next-cycle prediction modules, each hidden entirely when its field is absent. */
export function FutureTrendPanel({ decision }: { decision: StageDecision | null }) {
  const bar = decision?.next_bar_prediction;
  const cycle = decision?.next_cycle_prediction;

  if (!decision || (!bar && !cycle)) {
    return (
      <div className="panel">
        <h3>未来走势预测</h3>
        <p className="placeholder">暂无预测</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h3>未来走势预测</h3>

      {bar && (
        <div style={{ marginBottom: 12 }}>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>下一根K线</div>
          {bar.unpredictable ? (
            <div className="placeholder">不可预测</div>
          ) : (
            bar.probabilities && (
              <div style={{ color: DOMINANT_COLOR[dominantDirection(bar.probabilities)] }}>
                阳线的概率为{bar.probabilities.bullish}% · 阴线的概率为{bar.probabilities.bearish}% ·
                中性的概率为{bar.probabilities.neutral}%
              </div>
            )
          )}
          {bar.reasoning && <div className="reasoning-box">{bar.reasoning}</div>}
        </div>
      )}

      {cycle && (
        <div>
          <div style={{ fontSize: 12, color: "var(--fg-2)" }}>下一个市场周期</div>
          {cycle.unpredictable ? (
            <div className="placeholder">不可预测</div>
          ) : (
            <>
              {cycle.direction && (
                <div style={{ color: DOMINANT_COLOR[cycle.direction] }}>
                  {DIRECTION_ZH[cycle.direction] ?? cycle.direction}
                </div>
              )}
              {cycle.probabilities && (
                <div className="chip-row">
                  {Object.entries(cycle.probabilities)
                    .sort((a, b) => b[1] - a[1])
                    .map(([key, pct]) => (
                      <span className="chip" key={key}>
                        {key} {pct}%
                      </span>
                    ))}
                </div>
              )}
            </>
          )}
          {cycle.reasoning && <div className="reasoning-box">{cycle.reasoning}</div>}
        </div>
      )}
    </div>
  );
}
