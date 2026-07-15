import {
  Background,
  Controls,
  ReactFlow,
  ReactFlowProvider,
  useReactFlow,
  type Edge,
  type Node,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchSettingsSection } from "../api/paAgentApi";
import type { AnalysisRecord, DecisionFlowResponse } from "../types/domain";
import { fetchDecisionFlow } from "./decisionFlowApi";
import { layoutDecisionFlow } from "./layout";
import { decisionFlowNodeTypes } from "./nodes";

interface AutoPlaySettings {
  enabled: boolean;
  seconds: number;
}

/** Web port of `pa_agent/gui/decision_flow_viz.py::DecisionFlowVizPanel` --
 * branched flowchart of the AI walk (否=左 / 是=右 / 跳过=下), rendered with
 * react-flow (see phase-4 §0.1 decision) with CSS-driven animation instead of
 * the desktop's per-frame QPainter HUD effects (§0.2 decision: simplified
 * fidelity -- node highlight, flowing edge dots, terminal pulse glow). */
function DecisionFlowInner({ record }: { record: AnalysisRecord | null }) {
  const [flow, setFlow] = useState<DecisionFlowResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [autoPlay, setAutoPlay] = useState<AutoPlaySettings>({ enabled: false, seconds: 50 });
  const [playing, setPlaying] = useState(false);
  const [playPct, setPlayPct] = useState(0);
  const [fullscreen, setFullscreen] = useState(false);
  const rf = useReactFlow();
  const playTimerRef = useRef<number | null>(null);

  useEffect(() => {
    fetchSettingsSection("general")
      .then((g) =>
        setAutoPlay({
          enabled: Boolean(g.decision_flow_auto_play),
          seconds: Number(g.decision_flow_play_seconds) || 50,
        }),
      )
      .catch(() => setAutoPlay({ enabled: false, seconds: 50 }));
  }, []);

  const stage1 = record?.stage1_diagnosis ?? null;
  const stage2 = record?.stage2_decision ?? null;

  useEffect(() => {
    stopPlayback();
    if (!record) {
      setFlow(null);
      setError(null);
      return;
    }
    setError(null);
    fetchDecisionFlow({
      gate_trace: stage1?.gate_trace ?? [],
      decision_trace: stage2?.decision_trace ?? [],
      terminal: stage2?.terminal ?? null,
      gate_result: stage1?.gate_result ?? null,
      gate_shortcircuited: stage2?.gate_shortcircuited ?? false,
    })
      .then(setFlow)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
    // record identity changes on every new analysis; stage1/stage2 are derived from it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [record]);

  const { nodes, edges, activePathNodeIds } = useMemo(
    () => (flow ? layoutDecisionFlow(flow) : { nodes: [] as Node[], edges: [] as Edge[], activePathNodeIds: [] as string[] }),
    [flow],
  );

  useEffect(() => {
    if (!flow || nodes.length === 0) return;
    const id = window.setTimeout(() => rf.fitView({ padding: 0.15, duration: 260 }), 30);
    if (autoPlay.enabled) {
      const playId = window.setTimeout(() => startPlayback(), 320);
      return () => {
        window.clearTimeout(id);
        window.clearTimeout(playId);
      };
    }
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flow]);

  function stopPlayback() {
    if (playTimerRef.current !== null) {
      window.clearTimeout(playTimerRef.current);
      playTimerRef.current = null;
    }
    setPlaying(false);
    setPlayPct(0);
  }

  function startPlayback() {
    if (activePathNodeIds.length < 1) return;
    setPlaying(true);
    setPlayPct(0);
    const totalMs = Math.max(3, autoPlay.seconds) * 1000;
    const perNode = totalMs / activePathNodeIds.length;

    let i = 0;
    const step = () => {
      const nodeId = activePathNodeIds[i];
      const node = rf.getNode(nodeId);
      if (node) {
        const w = (node.measured?.width ?? node.width ?? 300) as number;
        const h = (node.measured?.height ?? node.height ?? 150) as number;
        rf.setCenter(node.position.x + w / 2, node.position.y + h / 2, {
          zoom: 0.85,
          duration: Math.min(900, perNode * 0.85),
        });
      }
      i += 1;
      setPlayPct(Math.round((i * 100) / activePathNodeIds.length));
      if (i >= activePathNodeIds.length) {
        playTimerRef.current = window.setTimeout(() => {
          setPlaying(false);
          rf.fitView({ padding: 0.15, duration: 400 });
        }, perNode);
        return;
      }
      playTimerRef.current = window.setTimeout(step, perNode);
    };
    step();
  }

  function handlePaneClick() {
    if (playing) stopPlayback();
  }

  return (
    <div className={`decision-flow-panel${fullscreen ? " fullscreen" : ""}`} data-testid="decision-flow-panel">
      <div className="decision-flow-header">
        <h3>决策路径可视化</h3>
        <div className="decision-flow-header-actions">
          {playing && <span className="decision-flow-play-status">路径播放中… {playPct}%（点击画面可停止）</span>}
          <button onClick={startPlayback} disabled={!flow || activePathNodeIds.length === 0}>
            {playing ? "重新播放" : "播放路径"}
          </button>
          <button onClick={() => setFullscreen((v) => !v)}>{fullscreen ? "退出全屏" : "全屏推演"}</button>
        </div>
      </div>
      <p className="decision-flow-sub">
        卡片 = 判断节点 · 左 = 否 / 右 = 是 · 亮线 = AI 实际路径 · 虚线框 = 未走分支含义 · 拖拽平移 · 滚轮缩放
      </p>

      {!record && <p className="placeholder">等待分析…提交后将显示左右分支决策流程图</p>}
      {error && (
        <p className="placeholder" style={{ color: "var(--danger)" }}>
          流程图加载失败：{error}
        </p>
      )}

      {record && flow && (
        <div className="decision-flow-canvas" onClick={handlePaneClick}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            nodeTypes={decisionFlowNodeTypes}
            fitView
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
            proOptions={{ hideAttribution: true }}
            minZoom={0.1}
            maxZoom={2.5}
          >
            <Background gap={32} color="var(--surface-3)" />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>
      )}
    </div>
  );
}

export function DecisionFlowPanel({ record }: { record: AnalysisRecord | null }) {
  return (
    <ReactFlowProvider>
      <DecisionFlowInner record={record} />
    </ReactFlowProvider>
  );
}
