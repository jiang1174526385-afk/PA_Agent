import { act } from "react";
import { createRoot, type Root } from "react-dom/client";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { FutureTrendPanel } from "./FutureTrendPanel";
import type { StageDecision } from "../types/domain";

(globalThis as { IS_REACT_ACT_ENVIRONMENT?: boolean }).IS_REACT_ACT_ENVIRONMENT = true;

// Same nested/flat `stage2_decision` shape concern as DecisionPanel (see
// docs/webui_migration/phase-7-execution-plan.md §0.1): FutureTrendPanel reads
// `next_bar_prediction`/`next_cycle_prediction` and must find them under either
// shape.
const FLAT_DECISION: StageDecision = {
  next_bar_prediction: {
    probabilities: { bullish: 60, bearish: 30, neutral: 10 },
    reasoning: "bar reasoning",
  },
  next_cycle_prediction: {
    direction: "bullish",
    probabilities: { bullish: 55, bearish: 45 },
    reasoning: "cycle reasoning",
  },
};

const NESTED_DECISION = {
  decision: { ...FLAT_DECISION },
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

describe("FutureTrendPanel", () => {
  it("shows a placeholder when there is no decision", () => {
    render(<FutureTrendPanel decision={null} />);
    expect(container.textContent).toContain("暂无预测");
  });

  it("shows a placeholder when neither prediction is present", () => {
    render(<FutureTrendPanel decision={{}} />);
    expect(container.textContent).toContain("暂无预测");
  });

  it("renders next-bar and next-cycle predictions from a flat-shape decision", () => {
    render(<FutureTrendPanel decision={FLAT_DECISION} />);
    expect(container.textContent).toContain("阳线的概率为60%");
    expect(container.textContent).toContain("bar reasoning");
    expect(container.textContent).toContain("cycle reasoning");
  });

  it("renders next-bar and next-cycle predictions from a nested-shape decision", () => {
    render(<FutureTrendPanel decision={NESTED_DECISION} />);
    expect(container.textContent).toContain("阳线的概率为60%");
    expect(container.textContent).toContain("bar reasoning");
    expect(container.textContent).toContain("cycle reasoning");
  });
});
