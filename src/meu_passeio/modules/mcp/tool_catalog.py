"""Catálogo de tools descobertas nos MCP Servers.

Mantém nome, descrição, schema de entrada e o server de origem de cada tool, valida
argumentos com JSON Schema e converte as tools para o formato do LLM — sempre filtrando
por uma allowlist (o agente só enxerga as tools permitidas para a etapa atual).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

SEPARATOR = "__"


@dataclass
class ToolDefinition:
    server: str
    tool: str
    description: str
    input_schema: dict[str, Any]
    read_only: bool = False
    _validator: Draft202012Validator | None = field(default=None, repr=False)

    @property
    def qualified_name(self) -> str:
        return f"{self.server}{SEPARATOR}{self.tool}"

    def validate_arguments(self, arguments: dict[str, Any]) -> str | None:
        if self._validator is None:
            self._validator = Draft202012Validator(self.input_schema)
        errors = sorted(self._validator.iter_errors(arguments), key=lambda e: list(e.path))
        if not errors:
            return None
        details = "; ".join(
            f"{'/'.join(str(p) for p in e.path) or '(raiz)'}: {e.message}" for e in errors[:5]
        )
        return f"Argumentos inválidos para {self.qualified_name}: {details}"

    def to_llm_tool(self) -> dict[str, Any]:
        return {
            "name": self.qualified_name,
            "description": f"[{self.server}] {self.description}".strip(),
            "input_schema": self.input_schema,
        }

    def public_view(self) -> dict[str, Any]:
        return {
            "name": self.qualified_name,
            "server": self.server,
            "tool": self.tool,
            "description": self.description,
            "read_only": self.read_only,
            "input_schema": self.input_schema,
        }


class ToolCatalog:
    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def replace(self, definitions: Iterable[ToolDefinition]) -> None:
        self._tools = {d.qualified_name: d for d in definitions}

    def all(self) -> list[ToolDefinition]:
        return list(self._tools.values())

    def get(self, qualified_name: str) -> ToolDefinition | None:
        return self._tools.get(qualified_name)

    def get_by_parts(self, server: str, tool: str) -> ToolDefinition | None:
        return self._tools.get(f"{server}{SEPARATOR}{tool}")

    @staticmethod
    def split(qualified_name: str) -> tuple[str, str]:
        server, _, tool = qualified_name.partition(SEPARATOR)
        return server, tool

    def select(self, allowlist: Iterable[str] | None = None) -> list[ToolDefinition]:
        """Seleciona tools por allowlist. Aceita 'server__tool' ou 'server__*'."""
        if allowlist is None:
            return self.all()
        patterns = list(allowlist)
        selected = []
        for definition in self._tools.values():
            for pattern in patterns:
                if pattern == definition.qualified_name or (
                    pattern.endswith("*") and definition.qualified_name.startswith(pattern[:-1])
                ):
                    selected.append(definition)
                    break
        return selected
