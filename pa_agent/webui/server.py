"""FastAPI application entry point for the PA Agent web UI (phase 1 skeleton).

Wires `AppContext.bootstrap()` at startup (same bootstrap used by the desktop
GUI), builds one `TwoStageOrchestrator` + `AnalysisRunner`, and mounts the
built SPA under a catch-all fallback route. Dev mode (`vite dev` on 5173)
talks to this process over CORS; the production build is served same-origin
and needs no CORS.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pa_agent.app_context import AppContext
from pa_agent.orchestrator.two_stage import TwoStageOrchestrator
from pa_agent.webui.api import analysis as analysis_api
from pa_agent.webui.api import chat as chat_api
from pa_agent.webui.api import decision_tree as decision_tree_api
from pa_agent.webui.api import demo as demo_api
from pa_agent.webui.api import kline as kline_api
from pa_agent.webui.api import models as models_api
from pa_agent.webui.api import reports as reports_api
from pa_agent.webui.api import settings as settings_api
from pa_agent.webui.deps import AppState
from pa_agent.webui.services.analysis_runner import AnalysisRunner

logger = logging.getLogger("pa_agent.webui")

_STATIC_DIR = Path(__file__).parent / "static" / "pa_agent_app"
_INDEX_HTML = _STATIC_DIR / "index.html"
_SPA_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}


def _build_orchestrator(ctx: AppContext) -> TwoStageOrchestrator:
    return TwoStageOrchestrator(
        client=ctx.client,
        assembler=ctx.assembler,
        router=ctx.router,
        validator=ctx.validator,
        pending_writer=ctx.pending_writer,
        exp_reader=ctx.exp_reader,
        settings=ctx.settings,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    ctx = AppContext.bootstrap()
    orchestrator = _build_orchestrator(ctx)
    app.state.pa_state = AppState(
        ctx=ctx,
        orchestrator=orchestrator,
        analysis_runner=AnalysisRunner(orchestrator),
    )
    try:
        yield
    finally:
        state: AppState = app.state.pa_state
        for broadcaster in list(state.broadcasters.values()):
            await broadcaster.stop()
        state.broadcasters.clear()
        try:
            ctx.data_source.disconnect()
        except Exception:
            logger.warning("data_source.disconnect() failed on shutdown", exc_info=True)


app = FastAPI(title="PA Agent", docs_url="/api/docs", redoc_url=None, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kline_api.router, prefix="/api")
app.include_router(kline_api.ws_router)
app.include_router(analysis_api.ws_router)
app.include_router(chat_api.ws_router)
app.include_router(chat_api.router, prefix="/api")
app.include_router(settings_api.router, prefix="/api")
app.include_router(models_api.router, prefix="/api")
app.include_router(reports_api.router, prefix="/api")
app.include_router(decision_tree_api.router, prefix="/api")
app.include_router(demo_api.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict:
    return {"status": "ok"}


if (_STATIC_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=_STATIC_DIR / "assets"), name="pa_agent_app_assets")


@app.get("/{rest:path}", include_in_schema=False)
async def spa_fallback(rest: str):
    if rest.startswith("api/") or rest.startswith("ws/"):
        return JSONResponse({"error": "not found"}, status_code=404)
    if _INDEX_HTML.exists():
        return FileResponse(_INDEX_HTML, headers=_SPA_HEADERS)
    return JSONResponse(
        {"error": "pa_agent frontend build not found", "path": str(_INDEX_HTML)},
        status_code=503,
        headers=_SPA_HEADERS,
    )
