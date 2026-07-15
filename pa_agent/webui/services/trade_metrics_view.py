"""Builds the `trade_metrics` sidecar payload sent alongside `/ws/analysis`'s
`"record"` message.

Ports the risk/reward + trader-equation display logic from
`pa_agent/gui/decision_panel.py` (which itself calls the pure functions in
`pa_agent/util/trade_metrics.py`) so the Web frontend can render the same
"交易者方程/预估胜率/风险回报比" indicators without any core-logic
duplication. Shared by `analysis_runner.py` and `demo_runner.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pa_agent.util.trade_metrics import (
    compute_risk_reward,
    max_risk_reward_ratio,
    min_risk_reward_ratio,
    passes_trader_equation,
)
from pa_agent.webui.services.decision_shape import decision_inner

if TYPE_CHECKING:
    from pa_agent.records.schema import AnalysisRecord

_NO_ORDER = "不下单"


def _parse_win_rate(value: object) -> float | None:
    """Parse `estimated_win_rate` (0-100, str or number) -- mirrors
    `pa_agent.util.trade_metrics._parse_win_rate`."""
    if value is None or value == "":
        return None
    try:
        return max(0.0, min(100.0, float(str(value).strip())))
    except (TypeError, ValueError):
        return None


def build_trade_metrics(record: "AnalysisRecord | None") -> dict[str, Any] | None:
    """Compute risk/reward + trader-equation metrics for a record's decision.

    Returns None when there is nothing to evaluate: no record, no decision
    payload (either shape), or the decision is "不下单" (no order placed).
    """
    if record is None:
        return None

    decision = decision_inner(record.stage2_decision)
    if decision is None:
        return None
    if decision.get("order_type") == _NO_ORDER:
        return None

    rr = compute_risk_reward(
        decision.get("entry_price"),
        decision.get("take_profit_price"),
        decision.get("stop_loss_price"),
        decision.get("order_direction"),
    )

    win_rate = _parse_win_rate(decision.get("estimated_win_rate"))

    risk_reward_ratio: float | None = None
    risk_reward_text: str | None = None
    trader_equation_passed: bool | None = None
    if rr is not None:
        risk_reward_ratio = float(rr["ratio"])
        risk_reward_text = str(rr["ratio_text"])
        if win_rate is not None:
            trader_equation_passed = passes_trader_equation(
                win_rate, float(rr["risk"]), float(rr["reward"])
            )

    decision_stance = getattr(record.meta, "decision_stance", None)
    return {
        "risk_reward_ratio": risk_reward_ratio,
        "risk_reward_text": risk_reward_text,
        "estimated_win_rate_pct": int(round(win_rate)) if win_rate is not None else None,
        "trader_equation_passed": trader_equation_passed,
        "min_risk_reward_ratio": min_risk_reward_ratio(decision_stance),
        "max_risk_reward_ratio": max_risk_reward_ratio(),
    }
