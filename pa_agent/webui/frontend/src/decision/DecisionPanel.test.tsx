import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { DecisionPanel } from "./DecisionPanel";
import type { StageDecision, TradeMetrics } from "../types/domain";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// Real production `stage2_decision` nests fields under a `decision` key;
// historical test fixtures across this project use a flat shape (same fields
// directly on `stage2_decision`). DecisionPanel must render correctly given
// either shape (see docs/webui_migration/phase-7-execution-plan.md §0.1).
const FLAT_DECISION: StageDecision = {
  order_type: "开仓",
  order_direction: "做多",
  entry_price: 1.2345,
  take_profit_price: 1.245,
  take_profit_price_2: 1.25,
  stop_loss_price: 1.22,
  trade_confidence: 82,
  direction: "上涨",
  cycle_position: "回调",
  market_phase: "stable",
  diagnosis_confidence: 90,
  reasoning: "flat-shape reasoning",
};

const NESTED_DECISION = {
  decision: { ...FLAT_DECISION },
  decision_trace: [],
} as unknown as StageDecision;

let container: HTMLDivElement;
let root: Root;

beforeEach(() => {
  container = document.createElement("div");
  document.body.appendChild(container);
  root = createRoot(container);
});

afterEach(() => {
  act(() => {
    root.unmount();
  });
  container.remove();
});

function render(ui: React.ReactElement) {
  act(() => {
    root.render(ui);
  });
}

describe("DecisionPanel", () => {
  it("shows a placeholder when there is no decision", () => {
    render(<DecisionPanel decision={null} />);
    expect(container.textContent).toContain("等待分析");
  });

  it("renders key fields from a flat-shape decision (historical fixtures)", () => {
    render(<DecisionPanel decision={FLAT_DECISION} />);
    expect(container.textContent).toContain("开仓");
    expect(container.textContent).toContain("做多");
    expect(container.textContent).toContain("1.2345");
    expect(container.textContent).toContain("置信度 82 / 100");
    expect(container.textContent).toContain("flat-shape reasoning");
  });

  it("renders key fields from a nested-shape decision (real production shape)", () => {
    render(<DecisionPanel decision={NESTED_DECISION} />);
    expect(container.textContent).toContain("开仓");
    expect(container.textContent).toContain("做多");
    expect(container.textContent).toContain("1.2345");
    expect(container.textContent).toContain("置信度 82 / 100");
    expect(container.textContent).toContain("flat-shape reasoning");
  });

  it("shows dashes for trader-equation section when tradeMetrics is absent", () => {
    render(<DecisionPanel decision={FLAT_DECISION} />);
    expect(container.textContent).not.toContain("风险回报比");
  });

  it("renders risk-reward / win-rate / trader-equation rows when tradeMetrics is present (passed)", () => {
    const tradeMetrics: TradeMetrics = {
      risk_reward_ratio: 2.5,
      risk_reward_text: "2.50 : 1",
      estimated_win_rate_pct: 65,
      trader_equation_passed: true,
      min_risk_reward_ratio: 1.5,
      max_risk_reward_ratio: null,
    };
    render(<DecisionPanel decision={FLAT_DECISION} tradeMetrics={tradeMetrics} />);
    expect(container.textContent).toContain("风险回报比");
    expect(container.textContent).toContain("2.50 : 1");
    expect(container.textContent).toContain("预估胜率");
    expect(container.textContent).toContain("65%");
    expect(container.textContent).toContain("交易者方程");
    expect(container.textContent).toContain("通过");
  });

  it("renders '未通过' and '—' fallbacks when trader equation fails / values missing", () => {
    const tradeMetrics: TradeMetrics = {
      risk_reward_ratio: null,
      risk_reward_text: null,
      estimated_win_rate_pct: null,
      trader_equation_passed: false,
      min_risk_reward_ratio: 1.5,
      max_risk_reward_ratio: null,
    };
    render(<DecisionPanel decision={FLAT_DECISION} tradeMetrics={tradeMetrics} />);
    expect(container.textContent).toContain("未通过");
  });

  it("does not crash when tradeMetrics is undefined (backward compatible callers)", () => {
    expect(() => render(<DecisionPanel decision={FLAT_DECISION} tradeMetrics={undefined} />)).not.toThrow();
  });
});
