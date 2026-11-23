"""Injeção de dependências do FastAPI (objetos criados no lifespan ficam em app.state)."""

from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Request

from meu_passeio.core.config import Settings
from meu_passeio.modules.mcp.client_manager import McpClientManager
from meu_passeio.modules.trips.repository import TripRepository
from meu_passeio.modules.trips.service import TripService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_mcp_manager(request: Request) -> McpClientManager:
    return request.app.state.mcp


async def get_trip_service(request: Request) -> AsyncIterator[TripService]:
    async with request.app.state.db.sessionmaker() as session:
        yield TripService(TripRepository(session))
