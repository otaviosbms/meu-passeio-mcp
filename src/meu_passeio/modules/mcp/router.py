"""Endpoints de inspeção da camada MCP (servers, catálogo de tools e chamada de debug)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException

from meu_passeio.api.dependencies import get_mcp_manager, get_settings_dep
from meu_passeio.core.config import Settings
from meu_passeio.modules.mcp.client_manager import McpClientManager
from meu_passeio.texts.api import Http, Routes

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.get("/servers")
async def list_servers(mcp: Annotated[McpClientManager, Depends(get_mcp_manager)]):
    return mcp.status()


@router.get("/tools")
async def list_tools(mcp: Annotated[McpClientManager, Depends(get_mcp_manager)]):
    return [t.public_view() for t in mcp.catalog.all()]


@router.post("/servers/{server}/reconnect")
async def reconnect(server: str, mcp: Annotated[McpClientManager, Depends(get_mcp_manager)]):
    if server not in mcp.connections:
        raise HTTPException(404, Http.MCP_SERVER_NOT_CONFIGURED)
    await mcp.connections[server].stop()
    await mcp.start()
    return mcp.status()


@router.post("/tools/{server}/{tool}", description=Routes.CALL_TOOL)
async def call_tool(
    server: str,
    tool: str,
    mcp: Annotated[McpClientManager, Depends(get_mcp_manager)],
    settings: Annotated[Settings, Depends(get_settings_dep)],
    arguments: Annotated[dict[str, Any], Body(examples=[{"total_budget": 400, "days": 1}])],
):
    if not settings.enable_tool_debug_endpoint:
        raise HTTPException(403, Http.DEBUG_ENDPOINT_DISABLED)
    result = await mcp.call_tool(server, tool, arguments)
    return {
        "server": result.server,
        "tool": result.tool,
        "ok": result.ok,
        "duration_ms": result.duration_ms,
        "data": result.data,
        "error": result.error,
    }
