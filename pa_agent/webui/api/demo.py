"""Read-only demo-record listing (GET /api/demo/records).

Playback itself goes over `/ws/analysis` with `mode: "demo"` (see
`pa_agent/webui/api/analysis.py`) -- this endpoint only feeds the picker.
"""

from __future__ import annotations

from fastapi import APIRouter

from pa_agent.demo.record_loader import (
    is_demo_playable,
    list_pending_record_paths,
    try_load_analysis_record,
)
from pa_agent.webui.schemas.demo import DemoRecordListResponse, DemoRecordSummary

router = APIRouter()


@router.get("/demo/records", response_model=DemoRecordListResponse)
async def list_demo_records() -> DemoRecordListResponse:
    items: list[DemoRecordSummary] = []
    for path in list_pending_record_paths():
        record = try_load_analysis_record(path)
        if record is None or not is_demo_playable(record):
            continue
        items.append(
            DemoRecordSummary(
                record_id=path.name,
                symbol=record.meta.symbol,
                timeframe=record.meta.timeframe,
                timestamp_local_iso=record.meta.timestamp_local_iso,
            )
        )
    return DemoRecordListResponse(records=items)
