"""Pydantic response models for K-line/data-source endpoints.

Mirrors `pa_agent/data/base.py`'s frozen dataclasses (`KlineBar`, `IndicatorBundle`,
`KlineFrame`) as JSON-serialisable shapes. Kept as a thin, hand-written mapping
(no auto-generation) per the project's WS schema policy.
"""

from __future__ import annotations

from pydantic import BaseModel

from pa_agent.data.base import IndicatorBundle, KlineBar, KlineFrame


class KlineBarOut(BaseModel):
    seq: int
    ts_open: float
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0.0
    pct_chg: float | None = None
    closed: bool = True

    @classmethod
    def from_bar(cls, bar: KlineBar) -> KlineBarOut:
        return cls(
            seq=bar.seq,
            ts_open=bar.ts_open,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            close=bar.close,
            volume=bar.volume,
            amount=bar.amount,
            pct_chg=bar.pct_chg,
            closed=bar.closed,
        )


def _nan_to_none(values: tuple[float, ...]) -> list[float | None]:
    # `json.dumps`'s default NaN literal isn't valid JSON -- browsers'
    # JSON.parse rejects it outright, so warm-up-period NaNs must become null.
    return [None if v != v else v for v in values]  # NaN != NaN


class IndicatorBundleOut(BaseModel):
    ema20: list[float | None]
    atr14: list[float | None]

    @classmethod
    def from_bundle(cls, bundle: IndicatorBundle) -> IndicatorBundleOut:
        return cls(ema20=_nan_to_none(bundle.ema20), atr14=_nan_to_none(bundle.atr14))


class KlineFrameOut(BaseModel):
    symbol: str
    timeframe: str
    bars: list[KlineBarOut]
    indicators: IndicatorBundleOut
    snapshot_ts_local_ms: int

    @classmethod
    def from_frame(cls, frame: KlineFrame) -> KlineFrameOut:
        return cls(
            symbol=frame.symbol,
            timeframe=frame.timeframe,
            bars=[KlineBarOut.from_bar(b) for b in frame.bars],
            indicators=IndicatorBundleOut.from_bundle(frame.indicators),
            snapshot_ts_local_ms=frame.snapshot_ts_local_ms,
        )


class DataSourceChoice(BaseModel):
    kind: str
    label: str


class SymbolsResponse(BaseModel):
    symbols: list[str]


class TimeframesResponse(BaseModel):
    timeframes: list[str]
