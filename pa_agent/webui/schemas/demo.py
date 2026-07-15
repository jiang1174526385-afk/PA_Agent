"""Read-only DTO for the demo-record picker (GET /api/demo/records).

Lists playable records from `RECORDS_PENDING_DIR` -- the same directory and
the same `is_demo_playable()` gate the desktop `_start_demo_mode("manual")`
file dialog and `pick_playable_demo_record()` (auto mode) use (see
`pa_agent/demo/record_loader.py`).
"""

from __future__ import annotations

from pydantic import BaseModel


class DemoRecordSummary(BaseModel):
    record_id: str
    symbol: str
    timeframe: str
    timestamp_local_iso: str


class DemoRecordListResponse(BaseModel):
    records: list[DemoRecordSummary]
