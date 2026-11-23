"""MCP Client Manager — mantém uma conexão lógica por MCP Server e executa tool calls.

Responsabilidades (seção 2 da arquitetura):
- conectar/inicializar servers configurados e descobrir tools;
- executar chamadas com timeout, retry seletivo e reconexão;
- normalizar resultados sem perder a origem (server/tool);
- registrar observabilidade (server, tool, duração, status) sem logar payloads.

O agente nunca vê detalhes de transporte: ele trabalha apenas com o ToolCatalog.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from contextvars import ContextVar
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import get_default_environment, stdio_client

from meu_passeio.modules.mcp.config import McpServerConfig
from meu_passeio.modules.mcp.tool_catalog import ToolCatalog, ToolDefinition

logger = logging.getLogger(__name__)

# Contexto de execução para correlacionar logs de tool calls com a viagem/execução.
current_trip_id: ContextVar[str | None] = ContextVar("current_trip_id", default=None)
current_run_id: ContextVar[str | None] = ContextVar("current_run_id", default=None)

ConnectionStatus = Literal["disconnected", "connecting", "connected", "failed"]


@dataclass
class ToolCallResult:
    server: str
    tool: str
    ok: bool
    data: Any = None
    error: str | None = None
    duration_ms: int = 0

    def to_model_payload(self) -> str:
        """Conteúdo enviado ao LLM — sempre com a origem dos dados."""
        if self.ok:
            return json.dumps(
                {"source": f"mcp:{self.server}/{self.tool}", "result": self.data},
                ensure_ascii=False,
                default=str,
            )
        return json.dumps(
            {"source": f"mcp:{self.server}/{self.tool}", "error": self.error}, ensure_ascii=False
        )


class McpServerUnavailable(RuntimeError):
    pass


@dataclass
class McpConnection:
    """Uma conexão stdio com um MCP Server, executada numa task dedicada.

    O ciclo de vida do ``stdio_client`` fica inteiro dentro da task (requisito do anyio),
    e a task é encerrada via ``_stop``.
    """

    config: McpServerConfig
    cwd: Path
    status: ConnectionStatus = "disconnected"
    tools: list[types.Tool] = field(default_factory=list)
    last_error: str | None = None
    session: ClientSession | None = None
    _task: asyncio.Task[None] | None = None
    _ready: asyncio.Event = field(default_factory=asyncio.Event)
    _stop: asyncio.Event = field(default_factory=asyncio.Event)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def name(self) -> str:
        return self.config.name

    def _params(self) -> StdioServerParameters:
        env = get_default_environment()
        env.update(self.config.resolved_env())
        env.setdefault("PYTHONIOENCODING", "utf-8")
        return StdioServerParameters(
            command=self.config.resolved_command(),
            args=self.config.args,
            env=env,
            cwd=self.config.cwd or str(self.cwd),
        )

    async def _run(self) -> None:
        try:
            async with stdio_client(self._params()) as (read, write):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools: list[types.Tool] = []
                    cursor: str | None = None
                    while True:
                        params = types.PaginatedRequestParams(cursor=cursor) if cursor else None
                        page = await session.list_tools(params=params)
                        tools.extend(page.tools)
                        cursor = page.next_cursor
                        if not cursor:
                            break
                    self.session, self.tools = session, tools
                    self.status, self.last_error = "connected", None
                    self._ready.set()
                    await self._stop.wait()
        except Exception as exc:  # noqa: BLE001
            self.last_error = f"{type(exc).__name__}: {exc}"
            self.status = "failed"
            logger.warning(
                "mcp_server_failed", extra={"mcp_server": self.name, "error": self.last_error}
            )
        finally:
            self.session = None
            if self.status != "failed":
                self.status = "disconnected"
            self._ready.set()

    async def start(self, timeout: float) -> None:
        async with self._lock:
            if self.status == "connected" and self._task and not self._task.done():
                return
            self._ready, self._stop = asyncio.Event(), asyncio.Event()
            self.status = "connecting"
            self._task = asyncio.create_task(self._run(), name=f"mcp:{self.name}")
            try:
                await asyncio.wait_for(self._ready.wait(), timeout=timeout)
            except TimeoutError:
                self.status, self.last_error = "failed", "timeout ao inicializar"
                self._stop.set()
            if self.status != "connected":
                raise McpServerUnavailable(f"{self.name}: {self.last_error}")

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            try:
                await asyncio.wait_for(self._task, timeout=10)
            except (TimeoutError, asyncio.CancelledError):
                self._task.cancel()
        self.status = "disconnected"


def _normalize(result: types.CallToolResult) -> Any:
    if result.structured_content is not None:
        return result.structured_content
    texts = [c.text for c in result.content if isinstance(c, types.TextContent)]
    joined = "\n".join(texts)
    try:
        return json.loads(joined)
    except (ValueError, TypeError):
        return joined


class McpClientManager:
    def __init__(
        self, configs: list[McpServerConfig], *, cwd: Path, connect_timeout: float = 20.0
    ) -> None:
        self._connections = {c.name: McpConnection(config=c, cwd=cwd) for c in configs if c.enabled}
        self._connect_timeout = connect_timeout
        self.catalog = ToolCatalog()

    @property
    def connections(self) -> dict[str, McpConnection]:
        return self._connections

    async def start(self) -> None:
        """Conecta a todos os servers em paralelo; falhas não derrubam a aplicação (fallback)."""

        async def _connect(conn: McpConnection) -> None:
            try:
                await conn.start(self._connect_timeout)
                logger.info(
                    "mcp_server_connected",
                    extra={"mcp_server": conn.name, "tools": [t.name for t in conn.tools]},
                )
            except McpServerUnavailable as exc:
                logger.error(
                    "mcp_server_unavailable", extra={"mcp_server": conn.name, "error": str(exc)}
                )

        await asyncio.gather(*(_connect(c) for c in self._connections.values()))
        self._rebuild_catalog()

    async def stop(self) -> None:
        await asyncio.gather(
            *(c.stop() for c in self._connections.values()), return_exceptions=True
        )

    def _rebuild_catalog(self) -> None:
        definitions: list[ToolDefinition] = []
        for conn in self._connections.values():
            if conn.status != "connected":
                continue
            allowed = set(conn.config.allowed_tools) if conn.config.allowed_tools else None
            for tool in conn.tools:
                if allowed is not None and tool.name not in allowed:
                    continue
                definitions.append(
                    ToolDefinition(
                        server=conn.name,
                        tool=tool.name,
                        description=tool.description or "",
                        input_schema=tool.input_schema,
                        read_only=bool(tool.annotations and tool.annotations.read_only_hint),
                    )
                )
        self.catalog.replace(definitions)

    async def _ensure(self, server: str) -> McpConnection:
        conn = self._connections.get(server)
        if conn is None:
            raise McpServerUnavailable(f"Server MCP desconhecido ou desabilitado: {server}")
        if conn.status != "connected" or conn.session is None:
            await conn.start(self._connect_timeout)
            self._rebuild_catalog()
        return conn

    async def call_tool(self, server: str, tool: str, arguments: dict[str, Any]) -> ToolCallResult:
        started = time.perf_counter()
        definition = self.catalog.get_by_parts(server, tool)
        result: ToolCallResult
        if definition is None:
            result = ToolCallResult(
                server, tool, ok=False, error="Tool não permitida ou inexistente."
            )
        else:
            validation_error = definition.validate_arguments(arguments)
            if validation_error:
                result = ToolCallResult(server, tool, ok=False, error=validation_error)
            else:
                result = await self._call_with_retries(server, tool, arguments)
        result.duration_ms = int((time.perf_counter() - started) * 1000)
        self._log(result)
        return result

    async def _call_with_retries(
        self, server: str, tool: str, arguments: dict[str, Any]
    ) -> ToolCallResult:
        conn = self._connections.get(server)
        attempts = 1 + (conn.config.retries if conn else 0)
        last_error = "erro desconhecido"
        for attempt in range(attempts):
            try:
                conn = await self._ensure(server)
                assert conn.session is not None
                raw = await asyncio.wait_for(
                    conn.session.call_tool(tool, arguments), timeout=conn.config.timeout_seconds
                )
                if not isinstance(raw, types.CallToolResult):
                    return ToolCallResult(server, tool, ok=False, error="Resposta MCP inesperada.")
                if raw.is_error:
                    # Erro de negócio/provedor: não é transitório do ponto de vista do client.
                    message = " ".join(
                        c.text for c in raw.content if isinstance(c, types.TextContent)
                    )
                    return ToolCallResult(server, tool, ok=False, error=message or "Erro na tool.")
                return ToolCallResult(server, tool, ok=True, data=_normalize(raw))
            except TimeoutError:
                last_error = f"Timeout após {conn.config.timeout_seconds if conn else '?'}s."
            except McpServerUnavailable as exc:
                return ToolCallResult(server, tool, ok=False, error=f"Server indisponível: {exc}")
            except Exception as exc:  # noqa: BLE001 — conexão caiu: tenta reconectar
                last_error = f"Falha de comunicação com o server ({type(exc).__name__})."
                if conn:
                    conn.status = "failed"
            if attempt < attempts - 1:
                await asyncio.sleep(0.5 * (attempt + 1))
        return ToolCallResult(server, tool, ok=False, error=last_error)

    def _log(self, result: ToolCallResult) -> None:
        result_count = None
        if isinstance(result.data, dict):
            for key in ("places", "days", "allocations", "by_category"):
                if isinstance(result.data.get(key), list):
                    result_count = len(result.data[key])
                    break
        logger.info(
            "mcp_tool_call",
            extra={
                "tripId": current_trip_id.get(),
                "workflowRunId": current_run_id.get(),
                "mcpServer": result.server,
                "tool": result.tool,
                "durationMs": result.duration_ms,
                "status": "success" if result.ok else "error",
                "resultCount": result_count,
            },
        )

    def status(self) -> list[dict[str, Any]]:
        return [
            {
                "name": c.name,
                "transport": c.config.transport,
                "status": c.status,
                "tools": [t.name for t in c.tools],
                "last_error": c.last_error,
            }
            for c in self._connections.values()
        ]
