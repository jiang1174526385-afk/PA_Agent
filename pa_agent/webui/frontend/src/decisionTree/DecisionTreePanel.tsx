import { useEffect, useRef, useState } from "react";
import type {
  AnalysisRecord,
  DecisionTreeReplayResponse,
  DecisionTreeSection,
} from "../types/domain";
import { fetchStaticDecisionTree, replayDecisionTrace } from "./decisionTreeApi";

const COLOR_VAR: Record<string, string> = {
  success: "var(--success)",
  danger: "var(--danger)",
  warning: "var(--warning)",
  muted: "var(--fg-3)",
  secondary: "var(--fg-2)",
};

function sectionIdOf(nodeId: string): string {
  return nodeId.split(".")[0] ?? nodeId;
}

/** Web port of pa_agent/gui/decision_tree_panel.py::DecisionTreePanel -- binary
 * decision tree path replay + full tree view, reading the same gate_trace/
 * decision_trace/terminal data as the desktop panel's `set_trace()`. */
export function DecisionTreePanel({ record }: { record: AnalysisRecord | null }) {
  const [sections, setSections] = useState<DecisionTreeSection[]>([]);
  const [replay, setReplay] = useState<DecisionTreeReplayResponse | null>(null);
  const [replayError, setReplayError] = useState<string | null>(null);
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const nodeRefs = useRef(new Map<string, HTMLTableRowElement>());

  useEffect(() => {
    fetchStaticDecisionTree()
      .then((r) => setSections(r.sections))
      .catch(() => setSections([]));
  }, []);

  const stage1 = record?.stage1_diagnosis ?? null;
  const stage2 = record?.stage2_decision ?? null;

  useEffect(() => {
    if (!record) {
      setReplay(null);
      setReplayError(null);
      return;
    }
    setReplayError(null);
    replayDecisionTrace({
      gate_trace: stage1?.gate_trace ?? [],
      decision_trace: stage2?.decision_trace ?? [],
      terminal: stage2?.terminal ?? null,
      gate_result: stage1?.gate_result ?? null,
      gate_shortcircuited: stage2?.gate_shortcircuited ?? false,
    })
      .then(setReplay)
      .catch((err) => setReplayError(err instanceof Error ? err.message : String(err)));
    // record identity changes on every new analysis; stage1/stage2 are derived from it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record]);

  const visitedIds = new Set(replay?.visited_ids ?? []);
  const rowByNodeId = new Map((replay?.rows ?? []).map((r) => [r.node_id, r]));
  const visitedSectionIds = new Set([...visitedIds].map(sectionIdOf));

  function handleRowClick(nodeId: string) {
    setSelectedNodeId(nodeId);
    const el = nodeRefs.current.get(nodeId);
    if (el) {
      el.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }

  return (
    <div className="panel decision-tree-panel" data-testid="decision-tree-panel">
      <h3>二元决策树</h3>

      {!record && <p className="placeholder">等待分析…</p>}
      {replayError && (
        <p className="placeholder" style={{ color: "var(--danger)" }}>
          决策树加载失败：{replayError}
        </p>
      )}

      {record && replay && (
        <>
          <div
            className="decision-tree-terminal-banner"
            style={{ color: COLOR_VAR[replay.terminal_banner.color_key] ?? "var(--fg)" }}
          >
            {replay.terminal_banner.text}
          </div>

          <div className="decision-tree-section-title">路径回放</div>
          <div className="placeholder" style={{ marginBottom: 6 }}>
            阶段一闸门 → 阶段二策略（悬停行可查看完整问题）
          </div>
          <div className="decision-tree-path-table-wrap">
            <table className="decision-tree-path-table">
              <thead>
                <tr>
                  <th>步</th>
                  <th>阶段</th>
                  <th>节点</th>
                  <th>回答</th>
                  <th>K线依据</th>
                  <th>理由</th>
                </tr>
              </thead>
              <tbody>
                {replay.rows.map((row) => (
                  <tr
                    key={`${row.phase}-${row.node_id}-${row.step}`}
                    title={row.tooltip}
                    data-node-id={row.node_id}
                    className={row.node_id === selectedNodeId ? "selected" : ""}
                    onClick={() => handleRowClick(row.node_id)}
                  >
                    <td>{row.step}</td>
                    <td>{row.phase_zh}</td>
                    <td>{row.node_id}</td>
                    <td style={{ color: COLOR_VAR[row.answer_color_key] ?? "var(--fg)" }}>
                      {row.answer_display}
                    </td>
                    <td>{row.basis}</td>
                    <td>{row.reason_display}</td>
                  </tr>
                ))}
                {replay.rows.length === 0 && (
                  <tr>
                    <td colSpan={6} className="placeholder">
                      无路径数据
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="decision-tree-section-title">完整决策树（已走过 = 高亮）</div>
          <div className="decision-tree-full-tree">
            {sections.map((sec) => (
              <details key={sec.id} data-section-id={sec.id} open={visitedSectionIds.has(sec.id)}>
                <summary>
                  §{sec.id} {sec.title}
                </summary>
                <table className="decision-tree-node-table">
                  <thead>
                    <tr>
                      <th>节点</th>
                      <th>问题</th>
                      <th>回答</th>
                      <th>K线依据</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sec.nodes.map((node) => {
                      const visited = visitedIds.has(node.id);
                      const row = rowByNodeId.get(node.id);
                      return (
                        <tr
                          key={node.id}
                          data-node-id={node.id}
                          ref={(el) => {
                            if (el) nodeRefs.current.set(node.id, el);
                            else nodeRefs.current.delete(node.id);
                          }}
                          className={
                            (visited ? "visited " : "unvisited ") +
                            (node.id === selectedNodeId ? "selected" : "")
                          }
                        >
                          <td>{node.id}</td>
                          <td>{node.question}</td>
                          <td style={row ? { color: COLOR_VAR[row.answer_color_key] } : undefined}>
                            {row?.answer_display ?? ""}
                          </td>
                          <td>{row && row.basis !== "—" ? row.basis : ""}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </details>
            ))}
          </div>

          {replay.gate_hint && <p className="placeholder">{replay.gate_hint}</p>}
        </>
      )}
    </div>
  );
}
