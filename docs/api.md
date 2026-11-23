# API HTTP

[← Voltar ao README](../README.md)

A API FastAPI inicia o MCP Server como processo filho, conecta-se a ele como MCP Client e expõe
as tools via HTTP. Também guarda roteiros.

```powershell
uvicorn meu_passeio.api.main:app --reload
```

Abra `http://localhost:8000/docs`. O server conectado é definido em `config/mcp_servers.yaml`.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `GET` | `/health` | Status da API e do MCP Server |
| `GET` | `/mcp/servers` | Conexões MCP, status e tools descobertas |
| `GET` | `/mcp/tools` | Catálogo de tools (nome, server, schema) |
| `POST` | `/mcp/tools/{server}/{tool}` | Executa uma tool (desative em produção) |
| `POST` | `/mcp/servers/{server}/reconnect` | Reconecta um server |
| `POST` | `/trips` | Salva um roteiro (`TripPlan`) |
| `GET` | `/trips` · `/trips/{id}` | Lista / detalha roteiros |
| `PUT` | `/trips/{id}` | Substitui um roteiro |
| `DELETE` | `/trips/{id}` | Remove um roteiro |

Exemplo — chamar uma tool pela API:

```powershell
curl -X POST http://localhost:8000/mcp/tools/meu-passeio/get_fuel_price `
  -H "content-type: application/json" `
  -d '{"state": "SP", "city": "Marília", "fuel": "gasolina"}'
```

## Docker

API + PostgreSQL:

```powershell
docker compose up --build
```

## `config/mcp_servers.yaml`

| Campo | Descrição |
|---|---|
| `command` / `args` | Como iniciar o server (`{python}` usa o interpretador atual) |
| `env` | Variáveis extras para o processo (`${VAR}` lê do ambiente) |
| `allowed_tools` | Allowlist opcional de tools |
| `timeout_seconds` / `retries` | Limites por chamada de tool |
