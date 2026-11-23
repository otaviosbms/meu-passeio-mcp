"""Textos compartilhados pelos MCP Servers."""


class ProviderErrors:
    TIMEOUT = "Provedor '{provider}' não respondeu a tempo."
    HTTP_STATUS = "Provedor '{provider}' retornou HTTP {status}."
    REQUEST_FAILED = "Falha ao consultar o provedor '{provider}'."
    LOCATION_NOT_FOUND = "Localização não encontrada: '{location}'."


class ToolErrors:
    INVALID_ARGUMENTS = "Argumentos inválidos: {details}"
    INTERNAL = "Erro interno ao executar a ferramenta."
