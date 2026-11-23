# Segurança e limites

[← Voltar ao README](../README.md)

- **Chaves** só em variáveis de ambiente; a do Google vai no header `X-Goog-Api-Key`, nunca em
  URLs, logs ou respostas.
- **Validação** dos argumentos de cada tool (Pydantic no server, JSON Schema no client).
- **Erros seguros**: falhas de provedor viram mensagens claras (`is_error`), sem detalhes internos.
- **Resiliência**: timeouts, retries e reconexão no client; failover entre instâncias do Overpass
  com circuit breaker; alternativas OSM/OSRM quando o Google falha.
- **Allowlist** de tools por server (`allowed_tools` no YAML da API).
- **Logs estruturados** (JSON) por chamada de tool: server, tool, duração, status e nº de
  resultados — sem payloads ou dados pessoais.
- **Endpoint de debug**: `POST /mcp/tools/{server}/{tool}` executa qualquer tool; desative em
  produção com `MEU_PASSEIO_ENABLE_TOOL_DEBUG_ENDPOINT=false`.
