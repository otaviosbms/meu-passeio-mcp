"""Textos da API FastAPI e do MCP Client Manager."""

APP_DESCRIPTION = (
    "Conecta MCP Servers de lugares, mapas, clima e orçamento, expõe suas tools "
    "via HTTP e persiste roteiros de viagem."
)


class Routes:
    """Descrições exibidas no OpenAPI (/docs)."""

    CALL_TOOL = "Executa uma tool diretamente (útil para debug/demo). Desative em produção."
    CREATE_TRIP = "Salva um roteiro montado pelo cliente."
    UPDATE_TRIP = "Substitui o roteiro de uma viagem."


class Http:
    MCP_SERVER_NOT_CONFIGURED = "Server MCP não configurado."
    DEBUG_ENDPOINT_DISABLED = "Endpoint de debug desabilitado."
    TRIP_NOT_FOUND = "Viagem não encontrada."


class Mcp:
    INIT_TIMEOUT = "timeout ao inicializar"
    SERVER_UNKNOWN = "Server MCP desconhecido ou desabilitado: {server}"
    SERVER_UNAVAILABLE = "Server indisponível: {error}"
    TOOL_NOT_ALLOWED = "Tool não permitida ou inexistente."
    UNEXPECTED_RESPONSE = "Resposta MCP inesperada."
    TOOL_ERROR = "Erro na tool."
    TIMEOUT = "Timeout após {seconds}s."
    COMMUNICATION_FAILURE = "Falha de comunicação com o server ({error_type})."
    UNKNOWN_ERROR = "erro desconhecido"
    INVALID_ARGUMENTS = "Argumentos inválidos para {tool}: {details}"
