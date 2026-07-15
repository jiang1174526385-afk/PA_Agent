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
