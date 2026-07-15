"""Decision tree replay API (phase 3): static tree + per-record trace formatting.

Reuses the pure trace-merging/formatting helpers in `pa_agent/ai/decision_tree.py`
(no PyQt dependency, see `pa_agent/gui/decision_tree_panel.py` for the desktop
mirror of this exact formatting) so the web frontend does not reimplement the
"merge gate_trace + decision_trace, format K-line basis suffix, pick answer
color" logic in TypeScript. No AI decision logic is touched here -- this
module only formats already-produced trace data (supplied by the caller, e.g.
extracted from an `/ws/analysis` `record` message) for display.
"""
from __future__ import annotations

from fastapi import APIRouter

from pa_agent.ai.decision_tree import (
    format_bar_basis_suffix,
    format_trace_answer,
    load_decision_tree,
    merge_traces,
    normalize_bar_range,
    plain_trace_question,
)
from pa_agent.webui.schemas.decision_tree import (
    DecisionTreeReplayRequest,
    DecisionTreeReplayResponse,
    DecisionTreeReplayRow,
    DecisionTreeStaticResponse,
    DecisionTreeTerminalBanner,
)

router = APIRouter()

_OUTCOME_ZH = {"wait": "等待", "reject": "放弃", "trade": "交易", "proceed": "继续评估"}
_PHASE_ZH = {"gate": "闸门", "decision": "策略"}
_ANSWER_COLOR_KEY = {
    "是": "success",
    "否": "danger",
    "中性": "warning",
    "等待": "warning",
    "不适用": "muted",
}


def _answer_color_key(answer: str) -> str:
    return _ANSWER_COLOR_KEY.get(answer, "secondary")


@router.get("/decision-tree/static")
async def get_static_tree() -> DecisionTreeStaticResponse:
    """Static binary decision tree definition (`二元决策.txt`), independent of
    any specific analysis run."""
    return DecisionTreeStaticResponse(**load_decision_tree())


@router.post("/decision-tree/replay")
async def replay(req: DecisionTreeReplayRequest) -> DecisionTreeReplayResponse:
    """Format one analysis run's gate_trace/decision_trace/terminal into path
    replay rows -- mirrors `DecisionTreePanel.set_trace`/`_fill_path_table`."""
    merged = merge_traces(req.gate_trace, req.decision_trace)

    visited_ids: list[str] = []
    for item in merged:
        nid = item.get("node_id")
        if nid and str(nid) not in visited_ids:
            visited_ids.append(str(nid))
    if req.terminal and req.terminal.get("node_id"):
        tid = str(req.terminal["node_id"])
        if tid not in visited_ids:
            visited_ids.append(tid)

    rows: list[DecisionTreeReplayRow] = []
    for idx, item in enumerate(merged):
        phase = str(item.get("phase", ""))
        node_id = str(item.get("node_id", "?"))
        question = plain_trace_question(item)
        basis = normalize_bar_range(item)
        answer = format_trace_answer(item) or str(item.get("answer", "—"))
        reason = str(item.get("reason", "") or "").strip()
        skipped = bool(item.get("skipped"))

        answer_display = f"{answer}（跳过）" if skipped else answer
        reason_suffix = (
            " [K线依据未标注]" if (not format_bar_basis_suffix(item) and not skipped) else ""
        )
        reason_display = (reason + reason_suffix) if (reason or reason_suffix) else "—"

        tip_lines = [question]
        if basis:
            tip_lines.append(f"K线依据：{basis}")
        if reason:
            tip_lines.append(f"理由：{reason}")

        base_ans = str(answer).split("（", 1)[0]

        rows.append(
            DecisionTreeReplayRow(
                step=idx + 1,
                phase=phase,
                phase_zh=_PHASE_ZH.get(phase, phase),
                node_id=node_id,
                answer_display=answer_display,
                answer_color_key=_answer_color_key(base_ans),
                basis=basis or "—",
                reason_display=reason_display,
                tooltip="\n".join(tip_lines),
            )
        )

    if req.terminal:
        outcome = str(req.terminal.get("outcome", ""))
        outcome_zh = _OUTCOME_ZH.get(outcome, outcome)
        label = req.terminal.get("label", "")
        node_id = req.terminal.get("node_id", "")
        color_key = "success" if outcome == "trade" else "warning"
        if outcome == "reject":
            color_key = "danger"
        banner = DecisionTreeTerminalBanner(
            text=f"终点 · §{node_id} · {outcome_zh}\n{label}", color_key=color_key
        )
    elif req.gate_result in ("wait", "unknown"):
        gr_zh = "等待" if req.gate_result == "wait" else "未知"
        banner = DecisionTreeTerminalBanner(
            text=(
                f"阶段一闸门：{gr_zh}（{req.gate_result}）\n"
                "未调用阶段二模型；下方为闸门路径。交易决策区为程序生成的「不下单」占位。"
            ),
            color_key="warning",
        )
    else:
        banner = DecisionTreeTerminalBanner(text="无终点信息", color_key="muted")

    if req.gate_shortcircuited:
        gate_hint = (
            "阶段一闸门未通过（wait/unknown）：已跳过阶段二 API 调用；"
            "决策页「不下单」与「不可预测」为程序根据闸门结论自动生成，非模型策略评估。"
        )
    elif req.gate_result:
        gate_hint = f"阶段一 gate_result：{req.gate_result}"
    else:
        gate_hint = ""

    return DecisionTreeReplayResponse(
        rows=rows, visited_ids=visited_ids, terminal_banner=banner, gate_hint=gate_hint
    )
