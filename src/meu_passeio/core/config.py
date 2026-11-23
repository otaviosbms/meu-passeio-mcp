"""Configuração da aplicação (lida de variáveis de ambiente / .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    # O .env é lido pelo caminho absoluto do projeto: o MCP Server é iniciado por clientes
    # (ex.: Claude Desktop) com outro diretório de trabalho.
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        env_prefix="MEU_PASSEIO_",
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

    # Google Maps Platform (Places API (New) + Routes API). Sem chave, o server usa
    # OpenStreetMap/OSRM como alternativa.
    google_maps_api_key: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_MAPS_API_KEY", "MEU_PASSEIO_GOOGLE_MAPS_API_KEY"),
    )
    google_language: str = "pt-BR"
    google_region: str = "BR"
    google_timeout_seconds: float = 20.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
