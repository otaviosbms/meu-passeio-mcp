"""MCP Server único do Meu Passeio — planejador de viagens.

Reúne as tools de lugares, mapas, clima e orçamento num só server e expõe o
prompt ``planejar_viagem``. O código de cada área fica no seu pacote
(``places/``, ``maps/``, ``weather/``, ``budget/``), que registra as próprias tools.

Execução (stdio):  python -m meu_passeio.mcp_server
Textos (instruções, prompt): meu_passeio/texts/server.py
"""

from __future__ import annotations

from typing import Annotated

from mcp.server.mcpserver import MCPServer
from pydantic import Field

from meu_passeio import __version__
from meu_passeio.core.logging import configure_logging
from meu_passeio.mcp_server.budget import tools as budget_tools
from meu_passeio.mcp_server.maps import tools as maps_tools
from meu_passeio.mcp_server.places import tools as places_tools
from meu_passeio.mcp_server.weather import tools as weather_tools
from meu_passeio.mcp_server.weather.provider import MAX_FORECAST_DAYS
from meu_passeio.texts import server as T

P = T.Prompts


def create_server() -> MCPServer:
    mcp = MCPServer(
        name=T.NAME,
        title=T.TITLE,
        version=__version__,
        instructions=T.INSTRUCTIONS.format(max_days=MAX_FORECAST_DAYS),
    )
    for module in (places_tools, maps_tools, weather_tools, budget_tools):
        module.register(mcp)

    @mcp.prompt(
        name="planejar_viagem", title=P.PLAN_TRIP_TITLE, description=P.PLAN_TRIP_DESCRIPTION
    )
    def planejar_viagem(
        destino: Annotated[str, Field(description=P.Args.DESTINATION)],
        dias: Annotated[str, Field(description=P.Args.DAYS)],
        origem: Annotated[str | None, Field(description=P.Args.ORIGIN)] = None,
        pessoas: Annotated[str | None, Field(description=P.Args.TRAVELERS)] = None,
        orcamento: Annotated[str | None, Field(description=P.Args.BUDGET)] = None,
        preferencias: Annotated[str | None, Field(description=P.Args.PREFERENCES)] = None,
    ) -> str:
        return P.PLAN_TRIP_TEMPLATE.format(
            destination=destino,
            days=dias,
            origin=origem or P.NOT_INFORMED,
            travelers=pessoas or P.NOT_INFORMED,
            budget=orcamento or P.NOT_INFORMED,
            preferences=preferencias or P.NOT_INFORMED,
        )

    return mcp


mcp = create_server()


def main() -> None:
    configure_logging()
    mcp.run("stdio")


if __name__ == "__main__":
    main()
