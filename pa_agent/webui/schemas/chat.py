"""DTOs for phase-5 free-chat / AI debug panel.

Debug-turn and prompt-files derivation mirror
`pa_agent/gui/main_window.py::_on_record_ready_impl` (Stage1/Stage2/exception
turns only -- follow-up chat turns are never added to the desktop debug tab
either, see phase-5-execution-plan.md §4). API-key masking is applied
server-side with `pa_agent.util.mask_secret.mask_secret`, mirroring
`DebugWidget._mask()`; the frontend never receives a plaintext API key.
"""
from __future__ import annotations

from pydantic import BaseModel

from pa_agent.records.schema import AnalysisRecord


class ChatDebugTurn(BaseModel):
    label: str
    system_prompt: str
    user_prompt: str
    raw_response: dict
    validation_info: str


class PromptFilesInfo(BaseModel):
    stage1_files: list[str]
    stage2_files: list[str]
    stage1_builtin: bool
    stage2_builtin: bool
    experience_count: int


class ChatDebugContextRequest(BaseModel):
    record: AnalysisRecord


class ChatDebugContextResponse(BaseModel):
    turns: list[ChatDebugTurn]
    prompt_files: PromptFilesInfo


# -- WS /ws/chat messages (documented for reference; not enforced at the WS
# layer, mirroring /ws/analysis's plain-dict message convention) --------------
#
# Client -> server:
#   {"type": "send", "text": str}
#   {"type": "cancel"}
#
# Server -> client:
#   {"type": "chat_reasoning", "chunk": str}
#   {"type": "chat_content", "chunk": str}
#   {"type": "chat_done", "content": str, "reasoning": str,
#    "usage": {"prompt_tokens": int, "cached_prompt_tokens": int,
#              "completion_tokens": int, "total_tokens": int,
#              "cache_hit_rate_pct": float},
#    "token_usage": {"context_used": int, "context_window": int,
#                    "total_input": int, "total_output": int,
#                    "total_cached_input": int}}
#   {"type": "chat_error", "message": str, "cancelled": bool}
