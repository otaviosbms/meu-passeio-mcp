"""Carregamento da configuração dos MCP Servers (YAML)."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

_ENV_PATTERN = re.compile(r"\$\{([A-Z0-9_]+)\}")


class McpServerConfig(BaseModel):
    name: str
    transport: Literal["stdio"] = "stdio"
    command: str
    args: list[str] = Field(default_factory=list)
    env: dict[str, str] = Field(default_factory=dict)
    cwd: str | None = None
    enabled: bool = True
    allowed_tools: list[str] | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)
    retries: int = Field(default=0, ge=0, le=3)

    def resolved_command(self) -> str:
        return sys.executable if self.command == "{python}" else self.command

    def resolved_env(self) -> dict[str, str]:
        return {
            key: _ENV_PATTERN.sub(lambda m: os.environ.get(m.group(1), ""), value)
            for key, value in self.env.items()
        }


def load_mcp_config(path: Path) -> list[McpServerConfig]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    servers = raw.get("mcpServers") or {}
    return [McpServerConfig(name=name, **(cfg or {})) for name, cfg in servers.items()]
