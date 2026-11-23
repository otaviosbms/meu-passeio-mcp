"""Configuração da aplicação (lida de variáveis de ambiente / .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore", env_prefix="MEU_PASSEIO_"
    )

    app_name: str = "Meu Passeio"
    environment: str = "development"
    log_level: str = "INFO"

    # Persistência — SQLite por padrão; use postgresql+asyncpg://... em produção/docker.
    database_url: str = f"sqlite+aiosqlite:///{(PROJECT_ROOT / 'meu_passeio.db').as_posix()}"

    # MCP
    mcp_config_path: Path = PROJECT_ROOT / "config" / "mcp_servers.yaml"
    mcp_connect_timeout_seconds: float = 20.0
    enable_tool_debug_endpoint: bool = True

    # LLM (Claude). A chave é lida pelo SDK de ANTHROPIC_API_KEY — nunca é enviada ao modelo.
    llm_model: str = "claude-opus-5-5"
    llm_effort: str = "medium"
    llm_max_tokens: int = 16000
    llm_enable_fallbacks: bool = True

    # Limites do agente (controle de custo)
    planner_max_tool_iterations: int = Field(default=12, ge=1, le=50)
    planner_max_tool_calls: int = Field(default=30, ge=1, le=200)
    planner_max_revisions: int = Field(default=1, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()
