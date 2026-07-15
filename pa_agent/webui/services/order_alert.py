"""Order-opportunity detection + notification trigger.

Shared by both the real-analysis and demo-replay branches of `/ws/analysis`
(see `pa_agent/webui/api/analysis.py`). Ports `main_window.py`'s
`_maybe_alert_order_opportunity()` (detect + broadcast) and
`_spawn_post_order_followup()`'s notification half (feishu/pushplus; the
trade-CSV-logging half is out of phase-6 scope -- see phase-6-completion-report.md).

Per phase-6-execution-plan.md §0.3 (confirmed with the user): this runs
unconditionally regardless of whether the record came from a real analysis or
a demo replay -- matching the desktop's own behaviour, where
`_maybe_alert_order_opportunity` is called from `_on_analysis_finished`
irrespective of `self._demo_mode`.
"""

from __future__ import annotations

import logging
import threading
from typing import TYPE_CHECKING

from pa_agent.gui.order_opportunity import format_order_alert_message, has_order_opportunity
from pa_agent.webui.services.decision_shape import decision_inner as _decision_inner

if TYPE_CHECKING:
    from fastapi import WebSocket

    from pa_agent.records.schema import AnalysisRecord
    from pa_agent.webui.deps import AppState

logger = logging.getLogger("pa_agent.webui")


async def maybe_alert_order_opportunity(
    websocket: "WebSocket",
    state: "AppState",
    record: "AnalysisRecord | None",
) -> None:
    """Detect a stage-2 order opportunity, broadcast it, and fire notifications."""
    if record is None:
        return
    decision_inner = _decision_inner(record.stage2_decision)
    if decision_inner is None:
        return

    settings = getattr(state.ctx, "settings", None) if state.ctx is not None else None
    general = getattr(settings, "general", None)
    if not bool(getattr(general, "alert_on_order_opportunity", True)):
        return
    threshold = int(getattr(general, "decision_confidence_threshold", 0) or 0)
    if not has_order_opportunity(decision_inner, confidence_threshold=threshold):
        return

    await websocket.send_json(
        {"type": "order_opportunity", "message": format_order_alert_message(decision_inner)}
    )
    _spawn_notify(state, decision_inner, record)


def _spawn_notify(state: "AppState", decision_inner: dict, record: "AnalysisRecord") -> None:
    """Run feishu/pushplus pushes off the event loop (network I/O, can take seconds)."""
    settings = getattr(state.ctx, "settings", None) if state.ctx is not None else None
    meta = record.meta
    stage2_full = record.stage2_decision

    def _run() -> None:
        try:
            from pa_agent.notify.feishu_notifier import send_order_signal as send_feishu_order
            from pa_agent.notify.pushplus_notifier import (
                pushplus_is_active,
                send_order_signal as send_pushplus_order,
            )

            send_feishu_order(
                decision_inner=decision_inner,
                stage2_full=stage2_full,
                symbol=meta.symbol,
                timeframe=meta.timeframe,
                chart_image_path=None,
                settings=settings,
            )
            if pushplus_is_active(settings):
                send_pushplus_order(
                    decision_inner=decision_inner,
                    stage2_full=stage2_full,
                    symbol=meta.symbol,
                    timeframe=meta.timeframe,
                    settings=settings,
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("下单信号通知失败（不影响主流程）: %s", exc)

    threading.Thread(target=_run, name="webui-order-notify", daemon=True).start()
