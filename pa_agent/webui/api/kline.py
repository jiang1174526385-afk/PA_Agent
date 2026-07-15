"""Data-source / K-line REST + WebSocket endpoints."""

from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from pa_agent.data.base import DataSourceError
from pa_agent.data.factory import DATA_SOURCE_CHOICES, create_data_source
from pa_agent.data.snapshot import INDICATOR_WARMUP_BARS, build_display_frame
from pa_agent.webui.deps import AppState
from pa_agent.webui.schemas.kline import (
    DataSourceChoice,
    KlineFrameOut,
    SymbolsResponse,
    TimeframesResponse,
)
from pa_agent.webui.services.refresh_broadcaster import RefreshBroadcaster

logger = logging.getLogger("pa_agent.webui")

router = APIRouter()
ws_router = APIRouter()


@router.get("/data-sources", response_model=list[DataSourceChoice])
async def list_data_sources() -> list[DataSourceChoice]:
    return [DataSourceChoice(kind=kind, label=label) for kind, label in DATA_SOURCE_CHOICES]


@router.get("/data-sources/{kind}/symbols", response_model=SymbolsResponse)
async def list_symbols(kind: str) -> SymbolsResponse:
    source = create_data_source(kind)
    try:
        await asyncio.to_thread(source.connect)
        symbols = await asyncio.to_thread(source.list_symbols)
    finally:
        await asyncio.to_thread(source.disconnect)
    return SymbolsResponse(symbols=symbols)


@router.get("/data-sources/{kind}/timeframes", response_model=TimeframesResponse)
async def list_timeframes(kind: str) -> TimeframesResponse:
    source = create_data_source(kind)
    return TimeframesResponse(timeframes=source.supported_timeframes())


@router.get("/kline/snapshot", response_model=KlineFrameOut)
async def kline_snapshot(source: str, symbol: str, timeframe: str, n: int = 100):
    ds = create_data_source(source)
    try:
        await asyncio.to_thread(ds.connect)
        await asyncio.to_thread(ds.subscribe, symbol, timeframe)
        bars = await asyncio.to_thread(ds.latest_snapshot, n + INDICATOR_WARMUP_BARS + 5)
    finally:
        await asyncio.to_thread(ds.disconnect)
    frame = build_display_frame(bars, n, symbol, timeframe)
    if frame is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="K线数据不足，无法生成快照")
    return KlineFrameOut.from_frame(frame)


async def _teardown_key(state: AppState, key) -> None:
    broadcaster = state.broadcasters.pop(key, None)
    if broadcaster is not None:
        await broadcaster.stop()
    if state.active_kline_key == key:
        state.active_kline_key = None


@ws_router.websocket("/ws/kline")
async def ws_kline(websocket: WebSocket) -> None:
    await websocket.accept()
    state: AppState = websocket.app.state.pa_state
    current_key = None

    try:
        while True:
            message = await websocket.receive_json()
            if message.get("type") != "subscribe":
                continue

            source = message.get("source", "mt5")
            symbol = message.get("symbol", "")
            timeframe = message.get("timeframe", "")
            n_bars = int(message.get("n_bars", 100))
            interval_ms = int(message.get("interval_ms", 1000))
            new_key = (source, symbol, timeframe)

            async with state.registry_lock:
                if current_key is not None:
                    old_broadcaster = state.broadcasters.get(current_key)
                    if old_broadcaster is not None:
                        old_broadcaster.remove_subscriber(websocket)
                        if old_broadcaster.subscriber_count == 0:
                            await _teardown_key(state, current_key)

                broadcaster = state.broadcasters.get(new_key)
                epoch = state.next_epoch()
                if broadcaster is None:
                    try:
                        ds = create_data_source(source)
                        broadcaster = RefreshBroadcaster(ds, symbol, timeframe, n_bars, interval_ms)
                        await broadcaster.start(epoch)
                    except DataSourceError as exc:
                        await websocket.send_json(
                            {"type": "error", "epoch": epoch, "message": str(exc)}
                        )
                        current_key = None
                        continue
                    state.broadcasters[new_key] = broadcaster
                broadcaster.add_subscriber(websocket)
                broadcaster._epoch = epoch
                state.active_kline_key = new_key
                current_key = new_key
                await websocket.send_json({"type": "subscribed", "epoch": epoch})
    except WebSocketDisconnect:
        pass
    finally:
        async with state.registry_lock:
            if current_key is not None:
                broadcaster = state.broadcasters.get(current_key)
                if broadcaster is not None:
                    broadcaster.remove_subscriber(websocket)
                    if broadcaster.subscriber_count == 0:
                        await _teardown_key(state, current_key)
