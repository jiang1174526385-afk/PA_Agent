"""Asyncio equivalent of `pa_agent/data/refresh_loop.py::RefreshLoop`.

Polls a `DataSource` on an interval and fans the resulting `KlineFrame` out to
all subscribed WebSocket connections for one `(source, symbol, timeframe)` key.
Backoff constants are copied verbatim from `RefreshLoop` so retry cadence
matches the desktop GUI.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from pa_agent.data.base import DataSource, DataSourceTransientError
from pa_agent.data.snapshot import INDICATOR_WARMUP_BARS, build_live_frame

if TYPE_CHECKING:
    from fastapi import WebSocket

logger = logging.getLogger("pa_agent.webui")

# Copied from pa_agent/data/refresh_loop.py::RefreshLoop (_BACKOFF_BASE_S / _MAX_BACKOFF_S).
_BACKOFF_BASE_S = 0.5
_MAX_BACKOFF_S = 10.0
_FAILURE_THRESHOLD_S = 5.0


class RefreshBroadcaster:
    """Polls `data_source` and broadcasts `KlineFrame`s to subscribed websockets.

    One instance owns one connected `DataSource` for the lifetime of the
    subscription (mirrors the desktop app's single active `RefreshLoop`).
    """

    def __init__(
        self,
        data_source: DataSource,
        symbol: str,
        timeframe: str,
        n_bars: int,
        interval_ms: int,
    ) -> None:
        self._source = data_source
        self._symbol = symbol
        self._timeframe = timeframe
        self._n_bars = n_bars
        self._interval_ms = interval_ms
        self._subscribers: set[WebSocket] = set()
        self._task: asyncio.Task | None = None
        self._epoch = 0
        self.latest_frame = None

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)

    async def start(self, epoch: int) -> None:
        self._epoch = epoch
        await asyncio.to_thread(self._source.connect)
        if hasattr(self._source, "set_exchange"):
            pass  # exchange selection (TradingView) is handled by the caller before start()
        await asyncio.to_thread(self._source.subscribe, self._symbol, self._timeframe)
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except (asyncio.CancelledError, Exception):
                pass
            self._task = None
        try:
            await asyncio.to_thread(self._source.unsubscribe)
        except Exception:
            logger.warning("unsubscribe failed during broadcaster stop", exc_info=True)
        try:
            await asyncio.to_thread(self._source.disconnect)
        except Exception:
            logger.warning("disconnect failed during broadcaster stop", exc_info=True)

    def add_subscriber(self, ws: WebSocket) -> None:
        self._subscribers.add(ws)

    def remove_subscriber(self, ws: WebSocket) -> None:
        self._subscribers.discard(ws)

    async def _broadcast(self, message: dict) -> None:
        dead = []
        for ws in list(self._subscribers):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._subscribers.discard(ws)

    async def _loop(self) -> None:
        consecutive_failures = 0
        n_fetch = self._n_bars + INDICATOR_WARMUP_BARS + 5
        failure_start: float | None = None
        loop = asyncio.get_running_loop()
        while True:
            t0 = loop.time()
            try:
                bars = await asyncio.to_thread(self._source.latest_snapshot, n_fetch)
                if consecutive_failures > 0:
                    await self._broadcast({"type": "status", "epoch": self._epoch, "message": ""})
                consecutive_failures = 0
                failure_start = None
                frame = build_live_frame(bars, self._n_bars, self._symbol, self._timeframe)
                if frame is not None:
                    self.latest_frame = frame
                    from pa_agent.webui.schemas.kline import KlineFrameOut

                    payload = KlineFrameOut.from_frame(frame).model_dump()
                    await self._broadcast({"type": "frame", "epoch": self._epoch, "frame": payload})
            except DataSourceTransientError as exc:
                consecutive_failures += 1
                now = loop.time()
                if failure_start is None:
                    failure_start = now
                message = str(exc).strip()
                if message:
                    await self._broadcast(
                        {"type": "status", "epoch": self._epoch, "message": message}
                    )
                elif now - failure_start >= _FAILURE_THRESHOLD_S:
                    await self._broadcast(
                        {"type": "status", "epoch": self._epoch, "message": "数据延迟"}
                    )
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception(
                    "RefreshBroadcaster unexpected error for %s/%s", self._symbol, self._timeframe
                )

            if consecutive_failures > 0:
                backoff = min(_BACKOFF_BASE_S * (2 ** (consecutive_failures - 1)), _MAX_BACKOFF_S)
                await asyncio.sleep(backoff)
                continue

            elapsed_s = loop.time() - t0
            await asyncio.sleep(max(0.0, (self._interval_ms / 1000.0) - elapsed_s))
