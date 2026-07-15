import { describe, expect, it } from "vitest";
import type { DecisionFlowResponse, DecisionFlowStep } from "../types/domain";
import { layoutDecisionFlow, NODE_H } from "./layout";

function step(overrides: Partial<DecisionFlowStep>): DecisionFlowStep {
  return {
    step: 1,
    phase: "gate",
    phase_zh: "闸门",
    node_id: "1.1",
    section: "",
    bar_range: "",
    question: "q",
    answer: "是",
    answer_color_key: "success",
    skipped: false,
    side: "right",
    overridden: false,
    program_answer: "",
    program_branch: "",
    override_reason: "",
    band_before: false,
    alt: { branch: "no", title: "否", outcome: "等待" },
    ...overrides,
  };
}

describe("layoutDecisionFlow", () => {
  it("places left/right branches on opposite sides with an untaken-branch stub", () => {
    const flow: DecisionFlowResponse = {
      steps: [
        step({ step: 1, node_id: "1.1", side: "left", alt: { branch: "yes", title: "是", outcome: "继续" } }),
        step({ step: 2, node_id: "1.2", side: "right", alt: { branch: "no", title: "否", outcome: "等待" } }),
      ],
      terminal: null,
      gate_shortcircuited: false,
      has_path: true,
    };

    const { nodes, edges, activePathNodeIds } = layoutDecisionFlow(flow);

    const decisionNodes = nodes.filter((n) => n.type === "flowDecision");
    const altNodes = nodes.filter((n) => n.type === "flowAlt");
    expect(decisionNodes).toHaveLength(2);
    expect(altNodes).toHaveLength(2);
    expect(activePathNodeIds).toEqual(["d-1.1-1", "d-1.2-2"]);

    // step 1 took 否(left): its decision node stays centered at x=0, the next
    // decision node (step 2) is shifted left, and the untaken 是 stub sits right.
    const d1 = decisionNodes.find((n) => n.id === "d-1.1-1")!;
    const d2 = decisionNodes.find((n) => n.id === "d-1.2-2")!;
    const stub1 = altNodes.find((n) => n.id === "alt-1.1-1")!;
    expect(d2.position.x).toBeLessThan(d1.position.x);
    expect(stub1.position.x).toBeGreaterThan(d1.position.x);

    // the active edge from step 1 goes to step 2's decision node; the alt
    // edge (dashed) goes to the stub.
    const mainEdge = edges.find((e) => e.id === "e-d-1.1-1-main")!;
    const altEdge = edges.find((e) => e.id === "e-d-1.1-1-alt")!;
    expect(mainEdge.target).toBe("d-1.2-2");
    expect(mainEdge.animated).toBe(true);
    expect(altEdge.target).toBe("alt-1.1-1");
    expect(altEdge.animated).toBe(false);
  });

  it("routes 'down' (skipped) steps straight to the next node with no stub", () => {
    const flow: DecisionFlowResponse = {
      steps: [step({ step: 1, node_id: "1.1", side: "down", skipped: true, alt: null })],
      terminal: { node_id: "9.0", outcome: "trade", outcome_zh: "交易", label: "做多", color_key: "success" },
      gate_shortcircuited: false,
      has_path: true,
    };

    const { nodes, edges, activePathNodeIds } = layoutDecisionFlow(flow);

    expect(nodes.some((n) => n.type === "flowAlt")).toBe(false);
    const terminalNode = nodes.find((n) => n.type === "flowTerminal")!;
    expect(terminalNode.id).toBe("terminal-9.0");
    expect(activePathNodeIds).toEqual(["d-1.1-1", "terminal-9.0"]);

    const mainEdge = edges.find((e) => e.id === "e-d-1.1-1-main")!;
    expect(mainEdge.target).toBe("terminal-9.0");
    expect(mainEdge.label).toBe("跳过");
  });

  it("inserts a phase band node before the gate->decision transition", () => {
    const flow: DecisionFlowResponse = {
      steps: [
        step({ step: 1, node_id: "1.1", phase: "gate", band_before: false, side: "down", alt: null }),
        step({ step: 2, node_id: "9.0", phase: "decision", band_before: true, side: "down", alt: null }),
      ],
      terminal: null,
      gate_shortcircuited: false,
      has_path: true,
    };

    const { nodes } = layoutDecisionFlow(flow);
    const band = nodes.find((n) => n.type === "flowBand")!;
    expect(band).toBeTruthy();
    expect(band.id).toBe("band-9.0-2");

    const d2 = nodes.find((n) => n.id === "d-9.0-2")!;
    const d1 = nodes.find((n) => n.id === "d-1.1-1")!;
    // the band reserves vertical space, so step 2 sits below step 1 + a gap
    // larger than a bare NODE_H hop would produce.
    expect(d2.position.y).toBeGreaterThan(d1.position.y + NODE_H);
  });
});
