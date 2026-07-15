import type { Edge, Node } from "@xyflow/react";
import type { DecisionFlowResponse } from "../types/domain";

// Node card sizes -- scaled-down web equivalents of the desktop QGraphicsScene
// constants in pa_agent/gui/decision_flow_viz.py (_NODE_W/_NODE_H/_STUB_W/...),
// same proportions, smaller absolute pixels since the web canvas is viewport-
// constrained rather than a freely pannable desktop scene.
export const NODE_W = 320;
export const NODE_H = 150;
export const STUB_W = 220;
export const STUB_H = 90;
export const TERMINAL_W = 300;
export const TERMINAL_H = 110;
const LEVEL_DY = 220;
const BRANCH_DX = 240;
const BAND_H = 56;

export interface FlowLayout {
  nodes: Node[];
  edges: Edge[];
  /** Decision node ids + terminal id in AI-walk order, for autoplay camera flight. */
  activePathNodeIds: string[];
}

function makeEdge(
  id: string,
  source: string,
  sourceHandle: string,
  target: string,
  label: string,
  active: boolean,
): Edge {
  return {
    id,
    source,
    sourceHandle,
    target,
    targetHandle: "top",
    label,
    animated: active,
    style: active
      ? { stroke: "var(--accent-3)", strokeWidth: 2.5 }
      : { stroke: "var(--fg-3)", strokeWidth: 1.5, strokeDasharray: "4 4", opacity: 0.6 },
    labelStyle: { fill: active ? "var(--accent-3)" : "var(--fg-3)", fontWeight: 700, fontSize: 11 },
    labelBgStyle: { fill: "#080c14", fillOpacity: 0.9 },
    zIndex: 1,
  };
}

/** Web port of `pa_agent/gui/decision_flow_viz.py::_layout_branched_path`.
 * Places decision cards left(否)/right(是)/down(跳过) and an untaken-branch
 * stub on the opposite side, then a terminal card at the end -- geometry only,
 * the domain data (branch side, alt outcome text, colors) comes pre-computed
 * from `POST /api/decision-tree/flow` (see that endpoint's docstring for why
 * the formatting itself lives in Python, not duplicated here). */
export function layoutDecisionFlow(flow: DecisionFlowResponse): FlowLayout {
  const nodes: Node[] = [];
  const activePathNodeIds: string[] = [];

  interface PlacedStep {
    id: string;
    x: number;
    y: number;
  }
  const placed: PlacedStep[] = [];

  let x = 0;
  let y = 0;

  for (const step of flow.steps) {
    if (step.band_before) {
      nodes.push({
        id: `band-${step.node_id}-${step.step}`,
        type: "flowBand",
        position: { x: x - 280, y },
        data: { title: "阶段二 · 策略评估" },
        draggable: false,
        selectable: false,
      });
      y += BAND_H;
    }

    const decisionId = `d-${step.node_id}-${step.step}`;
    nodes.push({
      id: decisionId,
      type: "flowDecision",
      position: { x: x - NODE_W / 2, y },
      data: { step },
      draggable: false,
    });
    activePathNodeIds.push(decisionId);
    placed.push({ id: decisionId, x, y });

    const ny = y + LEVEL_DY;
    let nextX = x;

    if (step.side === "left") {
      nextX = x - BRANCH_DX;
      if (step.alt) {
        const stubX = x + BRANCH_DX * 1.28;
        nodes.push({
          id: `alt-${step.node_id}-${step.step}`,
          type: "flowAlt",
          position: { x: stubX - STUB_W / 2, y: ny },
          data: { alt: step.alt },
          draggable: false,
          selectable: false,
        });
      }
    } else if (step.side === "right") {
      nextX = x + BRANCH_DX;
      if (step.alt) {
        const stubX = x - BRANCH_DX * 1.28;
        nodes.push({
          id: `alt-${step.node_id}-${step.step}`,
          type: "flowAlt",
          position: { x: stubX - STUB_W / 2, y: ny },
          data: { alt: step.alt },
          draggable: false,
          selectable: false,
        });
      }
    }

    x = nextX;
    y = ny;
  }

  let terminalId: string | null = null;
  if (flow.terminal) {
    const ty = y + LEVEL_DY - 20;
    terminalId = `terminal-${flow.terminal.node_id}`;
    nodes.push({
      id: terminalId,
      type: "flowTerminal",
      position: { x: x - TERMINAL_W / 2, y: ty },
      data: { terminal: flow.terminal },
      draggable: false,
      selectable: false,
    });
    activePathNodeIds.push(terminalId);

    if (flow.gate_shortcircuited) {
      nodes.push({
        id: "band-short",
        type: "flowBand",
        position: { x: x - 280, y: ty - 50 },
        data: { title: "阶段二已短路" },
        draggable: false,
        selectable: false,
      });
    }
  } else if (flow.gate_shortcircuited && placed.length > 0) {
    const last = placed[placed.length - 1];
    nodes.push({
      id: "band-short",
      type: "flowBand",
      position: { x: last.x - 280, y: last.y + NODE_H + 30 },
      data: { title: "阶段二已短路" },
      draggable: false,
      selectable: false,
    });
  }

  // Each decision node's "active" edge targets the next decision node in the
  // walk (or the terminal, if this was the last step); the untaken side gets
  // a dashed inactive edge to its stub card.
  const edges: Edge[] = [];
  for (let i = 0; i < placed.length; i++) {
    const cur = placed[i];
    const next = placed[i + 1] ?? null;
    const targetId = next ? next.id : terminalId;
    if (!targetId) continue;

    const step = flow.steps[i];
    if (step.side === "down") {
      edges.push(makeEdge(`e-${cur.id}-main`, cur.id, "bottom", targetId, step.skipped ? "跳过" : "→", true));
    } else if (step.side === "left") {
      edges.push(makeEdge(`e-${cur.id}-main`, cur.id, "left", targetId, "否", true));
      if (step.alt) {
        edges.push(
          makeEdge(`e-${cur.id}-alt`, cur.id, "right", `alt-${step.node_id}-${step.step}`, "是", false),
        );
      }
    } else if (step.side === "right") {
      edges.push(makeEdge(`e-${cur.id}-main`, cur.id, "right", targetId, "是", true));
      if (step.alt) {
        edges.push(
          makeEdge(`e-${cur.id}-alt`, cur.id, "left", `alt-${step.node_id}-${step.step}`, "否", false),
        );
      }
    }
  }

  return { nodes, edges, activePathNodeIds };
}
