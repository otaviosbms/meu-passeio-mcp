"""Aplicação FastAPI — host MCP do Meu Passeio.

Executar:  uvicorn meu_passeio.api.main:app --reload
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from meu_passeio import __version__
from meu_passeio.core.config import PROJECT_ROOT, Settings, get_settings
from meu_passeio.core.logging import configure_logging
from meu_passeio.db.session import Database
from meu_passeio.modules.mcp.client_manager import McpClientManager
from meu_passeio.modules.mcp.config import load_mcp_config
from meu_passeio.modules.mcp.router import router as mcp_router
from meu_passeio.modules.planner.graph import PlannerGraph
from meu_passeio.modules.planner.llm import LLMClient
from meu_passeio.modules.planner.service import PlannerService
from meu_passeio.modules.trips.router import router as trips_router

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None, *, llm: LLMClient | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        db = Database(settings.database_url)
        await db.create_all()

        mcp = McpClientManager(
            load_mcp_config(settings.mcp_config_path),
            cwd=PROJECT_ROOT,
            connect_timeout=settings.mcp_connect_timeout_seconds,
        )
        await mcp.start()

        graph = PlannerGraph(settings, llm or LLMClient(settings), mcp)
        app.state.settings = settings
        app.state.db = db
        app.state.mcp = mcp
        app.state.planner = PlannerService(graph)
        logger.info("app_started", extra={"tools": len(mcp.catalog.all())})
        try:
            yield
        finally:
            await mcp.stop()
            await db.dispose()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description=(
            "Planejador de viagens com IA. O backend é o host MCP: conecta MCP Servers de "
            "lugares, mapas, clima e orçamento e orquestra o planejamento com LangGraph."
        ),
        lifespan=lifespan,
    )

    @app.get("/health", tags=["health"])
    async def health():
        mcp: McpClientManager = app.state.mcp
        servers = {s["name"]: s["status"] for s in mcp.status()}
        degraded = any(status != "connected" for status in servers.values())
        return {"status": "degraded" if degraded else "ok", "mcp_servers": servers}

    app.include_router(trips_router)
    app.include_router(mcp_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("meu_passeio.api.main:app", host="0.0.0.0", port=8000)
