import { Handle, Position, type NodeProps } from "@xyflow/react";
import type { CSSProperties } from "react";
import type { DecisionFlowAlt, DecisionFlowStep, DecisionFlowTerminal } from "../types/domain";

const COLOR_VAR: Record<string, string> = {
  success: "var(--success)",
  danger: "var(--danger)",
  warning: "var(--warning)",
  muted: "var(--fg-3)",
  secondary: "var(--accent-3)",
};

const HANDLE_HIDDEN: CSSProperties = { opacity: 0, pointerEvents: "none" };

/** Web port of `pa_agent/gui/decision_flow_viz.py::_DecisionNode` -- the
 * "large card" for an active decision on the AI walk path. Visual fidelity is
 * intentionally simplified per the phase-4 §0.2 decision (CSS highlight/glow
 * instead of hand-painted HUD corner brackets / scanlines). */
export function FlowDecisionNode({ data }: NodeProps) {
  const step = (data as { step: DecisionFlowStep }).step;
  const accent = step.skipped ? "var(--fg-3)" : (COLOR_VAR[step.answer_color_key] ?? "var(--accent-3)");
  const meta = [step.section, step.bar_range].filter(Boolean).join(" · ");

  return (
    <div
      className={`flow-decision-node${step.skipped ? " skipped" : ""}`}
      style={{ ["--flow-accent" as string]: accent } as CSSProperties}
      title={step.question}
      data-testid="flow-decision-node"
      data-node-id={step.node_id}
    >
      <Handle type="target" position={Position.Top} id="top" style={HANDLE_HIDDEN} />
      <Handle type="source" position={Position.Bottom} id="bottom" style={{ ...HANDLE_HIDDEN, left: "50%" }} />
      <Handle type="source" position={Position.Bottom} id="left" style={{ ...HANDLE_HIDDEN, left: "38%" }} />
      <Handle type="source" position={Position.Bottom} id="right" style={{ ...HANDLE_HIDDEN, left: "62%" }} />

      <div className="flow-node-stripe" />
      {step.overridden && <div className="flow-node-override-badge">AI覆盖</div>}

      <div className="flow-node-header">
        <span>
          #{String(step.step).padStart(2, "0")} · {step.phase_zh}
        </span>
        <span className="flow-node-id">§{step.node_id}</span>
      </div>
      {meta && <div className="flow-node-meta">{meta}</div>}
      <div className="flow-node-question">{step.question}</div>
      <div className="flow-node-footer">
        结论：{step.answer}
        {step.skipped ? "（跳过）" : ""}
      </div>
    </div>
  );
}

/** Web port of `_AltBranchNode` -- the untaken branch, per 二元决策树. */
export function FlowAltNode({ data }: NodeProps) {
  const alt = (data as { alt: DecisionFlowAlt }).alt;
  const accent = alt.branch === "yes" ? "var(--success)" : "var(--danger)";

  return (
    <div
      className="flow-alt-node"
      style={{ ["--flow-accent" as string]: accent } as CSSProperties}
      title={alt.outcome}
      data-testid="flow-alt-node"
    >
      <Handle type="target" position={Position.Top} id="top" style={HANDLE_HIDDEN} />
      <div className="flow-alt-title">未走分支：{alt.title}</div>
      <div className="flow-alt-outcome">{alt.outcome}</div>
    </div>
  );
}

/** Web port of `_TerminalNode` -- final verdict card; pulsing glow via CSS
 * animation instead of the desktop's per-frame QPainter sine pulse. */
export function FlowTerminalNode({ data }: NodeProps) {
  const terminal = (data as { terminal: DecisionFlowTerminal }).terminal;
  const accent = COLOR_VAR[terminal.color_key] ?? "var(--accent-3)";

  return (
    <div
      className="flow-terminal-node"
      style={{ ["--flow-accent" as string]: accent } as CSSProperties}
      title={terminal.label}
      data-testid="flow-terminal-node"
    >
      <Handle type="target" position={Position.Top} id="top" style={HANDLE_HIDDEN} />
      <div className="flow-terminal-header">
        FINAL VERDICT // §{terminal.node_id}
      </div>
      <div className="flow-terminal-outcome">{terminal.outcome_zh.toUpperCase()}</div>
      <div className="flow-terminal-label">{terminal.label}</div>
    </div>
  );
}

/** Web port of `_PhaseBandItem` -- the "阶段二·策略评估" divider. */
export function FlowBandNode({ data }: NodeProps) {
  const title = (data as { title: string }).title;
  return (
    <div className="flow-band-node">
      <span className="flow-band-line" />
      <span className="flow-band-title">{title}</span>
      <span className="flow-band-line" />
    </div>
  );
}

export const decisionFlowNodeTypes = {
  flowDecision: FlowDecisionNode,
  flowAlt: FlowAltNode,
  flowTerminal: FlowTerminalNode,
  flowBand: FlowBandNode,
};
