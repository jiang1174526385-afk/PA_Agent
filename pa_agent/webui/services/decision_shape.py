"""Shared helper for unwrapping stage-2 decision JSON's two real-world shapes.

Production stage-2 responses nest the actual decision fields under a
``"decision"`` key (alongside ``decision_trace``, see
`pa_agent/ai/prompt_assembler.py`'s stage-2 output contract), while this
project's test fixtures (webui + e2e) historically use a flat shape with the
fields directly at the top level. Both need to be handled uniformly by any
code that reads `AnalysisRecord.stage2_decision`.

Originally written as `order_alert.py::_decision_inner`; extracted here so
`trade_metrics_view.py` can reuse the exact same unwrapping logic without
duplicating it.
"""

from __future__ import annotations


def decision_inner(stage2_decision: dict | None) -> dict | None:
    """Unwrap the real (nested) `{"decision": {...}}` stage-2 JSON shape.

    Falls back to treating *stage2_decision* itself as already-flat, which is
    the shape this webui test suite's fake orchestrators use (see
    tests/webui/conftest.py::_make_record / e2e/conftest.py::_build_record).
    """
    if not isinstance(stage2_decision, dict):
        return None
    inner = stage2_decision.get("decision")
    return inner if isinstance(inner, dict) else stage2_decision
