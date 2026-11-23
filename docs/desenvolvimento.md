# Desenvolvimento

[← Voltar ao README](../README.md)

## Testes

```powershell
pytest
```

46 testes, sem chamadas de rede (exceto o MCP Server real via stdio):

- unitários: cálculos de orçamento, catálogo de tools, horários de funcionamento, cálculo solar,
  médias climáticas, feriados e Páscoa;
- Google Places e Routes com respostas simuladas (`tests/google_fakes.py` e a fixture
  `fake_google`), incluindo fallback e garantia de que a chave não vaza em mensagens;
- ANP e PTAX com dados simulados;
- integração real via stdio entre o MCP Client Manager e o server;
- ponta a ponta da API (`/health`, `/mcp/*`, `/trips`).

## Lint

```powershell
ruff check src tests
ruff format src tests
```

## Adicionar uma tool

1. Escreva a função em `src/meu_passeio/mcp_server/<área>/tools.py`, decorada com `@safe_tool`,
   com parâmetros tipados (`Annotated[..., Field(description=...)]`).
2. Coloque descrição, parâmetros, notas e erros em `src/meu_passeio/texts/<área>.py`.
3. Registre em `register(mcp)` com `mcp.add_tool(func, description=..., annotations=...)`.
4. Se a tool chama um provedor externo, ponha a lógica em `service.py` e o acesso HTTP num
   módulo de provider; erros do provedor devem virar `ProviderError` com mensagem segura.
5. Atualize a lista de tools esperadas em `tests/test_mcp_integration.py` e a contagem em
   `tests/test_api.py`, e escreva os testes da tool.

Veja o padrão de cada área em [Arquitetura](arquitetura.md).
