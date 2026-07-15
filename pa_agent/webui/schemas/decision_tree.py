"""Response/request DTOs for the phase-3 decision tree replay API."""
from __future__ import annotations

from pydantic import BaseModel


class DecisionTreeNode(BaseModel):
    id: str
    question: str


class DecisionTreeSection(BaseModel):
    id: str
    title: str
    nodes: list[DecisionTreeNode]


class DecisionTreeStaticResponse(BaseModel):
    version: int
    source: str
    sections: list[DecisionTreeSection]


class DecisionTreeReplayRequest(BaseModel):
    gate_trace: list[dict] | None = None
    decision_trace: list[dict] | None = None
    terminal: dict | None = None
    gate_result: str | None = None
    gate_shortcircuited: bool = False


class DecisionTreeReplayRow(BaseModel):
    step: int
    phase: str
    phase_zh: str
    node_id: str
    answer_display: str
    answer_color_key: str  # "success" | "danger" | "warning" | "muted" | "secondary"
    basis: str
    reason_display: str
    tooltip: str


class DecisionTreeTerminalBanner(BaseModel):
    text: str
    color_key: str  # "success" | "warning" | "danger" | "muted"


class DecisionTreeReplayResponse(BaseModel):
    rows: list[DecisionTreeReplayRow]
    visited_ids: list[str]
    terminal_banner: DecisionTreeTerminalBanner
    gate_hint: str


# -- Phase 4: DecisionFlowViz (branched flowchart) --------------------------


class DecisionFlowAlt(BaseModel):
    """Untaken branch stub -- what the other answer would have meant."""

    branch: str  # "yes" | "no"
    title: str  # "是" | "否"
    outcome: str


class DecisionFlowStep(BaseModel):
    step: int
    phase: str
    phase_zh: str
    node_id: str
    section: str
    bar_range: str
    question: str
    answer: str  # includes branch suffix, e.g. "是 · 突破"
    answer_color_key: str
    skipped: bool
    side: str  # "left" | "right" | "down"
    overridden: bool
    program_answer: str
    program_branch: str
    override_reason: str
    band_before: bool  # insert a "阶段二·策略评估" phase band before this step
    alt: DecisionFlowAlt | None = None


class DecisionFlowTerminal(BaseModel):
    node_id: str
    outcome: str
    outcome_zh: str
    label: str
    color_key: str


class DecisionFlowResponse(BaseModel):
    steps: list[DecisionFlowStep]
    terminal: DecisionFlowTerminal | None = None
    gate_shortcircuited: bool = False
    has_path: bool
