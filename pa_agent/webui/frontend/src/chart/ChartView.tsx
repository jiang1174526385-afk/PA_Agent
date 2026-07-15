import type { KlineFrame, StageDecision } from "../types/domain";
import { useLightweightChart } from "./useLightweightChart";

export function ChartView({
  frame,
  decision,
}: {
  frame: KlineFrame | null;
  decision: StageDecision | null;
}) {
  const { containerRef } = useLightweightChart(frame, decision);
  return (
    <div className="chart-pane" data-testid="chart-view">
      <div ref={containerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}
