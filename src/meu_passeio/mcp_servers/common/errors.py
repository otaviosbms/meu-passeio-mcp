"""Converte erros de provider em ToolError (resultado MCP com is_error=True e mensagem segura)."""

from __future__ import annotations

import functools
import logging
from collections.abc import Awaitable, Callable
from typing import ParamSpec, TypeVar

from mcp.server.mcpserver.exceptions import ToolError

from meu_passeio.mcp_servers.common.http import ProviderError
from meu_passeio.texts.common import ToolErrors

P = ParamSpec("P")
R = TypeVar("R")

logger = logging.getLogger(__name__)


def safe_tool(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
    @functools.wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        try:
            return await func(*args, **kwargs)
        except ProviderError as exc:
            raise ToolError(str(exc)) from exc
        except ValueError as exc:
            raise ToolError(ToolErrors.INVALID_ARGUMENTS.format(details=exc)) from exc
        except Exception as exc:  # noqa: BLE001 — nunca vazar detalhes internos ao client
            logger.exception("tool_unexpected_error", extra={"tool": func.__name__})
            raise ToolError(ToolErrors.INTERNAL) from exc

    return wrapper
