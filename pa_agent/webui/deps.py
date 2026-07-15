"""FastAPI dependency wiring: shared app state, `AppContext` access, broadcaster
registry, and the single-flight analysis runner.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from fastapi import Request

from pa_agent.app_context import AppContext

if TYPE_CHECKING:
    from pa_agent.data.base import KlineFrame
    from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
    from pa_agent.records.schema import AnalysisRecord
    from pa_agent.webui.services.analysis_runner import AnalysisRunner
    from pa_agent.webui.services.refresh_broadcaster import RefreshBroadcaster

KlineKey = tuple[str, str, str]  # (source_kind, symbol, timeframe)


@dataclass
class AppState:
    ctx: AppContext
    orchestrator: TwoStageOrchestrator
    analysis_runner: AnalysisRunner
    registry_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    broadcasters: dict[KlineKey, RefreshBroadcaster] = field(default_factory=dict)
    epoch_counter: int = 0
    active_kline_key: KlineKey | None = None
    last_analysis_record: AnalysisRecord | None = None

    def next_epoch(self) -> int:
        self.epoch_counter += 1
        return self.epoch_counter

    def active_frame(self) -> KlineFrame | None:
        if self.active_kline_key is None:
            return None
        broadcaster = self.broadcasters.get(self.active_kline_key)
        return broadcaster.latest_frame if broadcaster else None


def get_app_state(request: Request) -> AppState:
    return request.app.state.pa_state


def get_ctx(request: Request) -> AppContext:
    return get_app_state(request).ctx
