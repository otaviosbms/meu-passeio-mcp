# Configuração

[← Voltar ao README](../README.md)

Variáveis lidas do `.env` na raiz do projeto (modelo em `.env.example`):

| Variável | Padrão | Descrição |
|---|---|---|
| `GOOGLE_MAPS_API_KEY` | — | Chave do Google Maps Platform (opcional, recomendada). Veja [Chave do Google Maps](google-maps.md) |
| `MEU_PASSEIO_GOOGLE_LANGUAGE` / `MEU_PASSEIO_GOOGLE_REGION` | `pt-BR` / `BR` | Idioma e região das respostas do Google |
| `MEU_PASSEIO_DATABASE_URL` | SQLite em `meu_passeio.db` | Banco dos roteiros (`postgresql+asyncpg://…` para PostgreSQL) |
| `MEU_PASSEIO_LOG_LEVEL` | `INFO` | Nível de log (JSON no stderr) |
| `MEU_PASSEIO_ENABLE_TOOL_DEBUG_ENDPOINT` | `true` | Habilita `POST /mcp/tools/{server}/{tool}` |
| `MEU_PASSEIO_HTTP_USER_AGENT` | genérico | User-Agent para OSM/Nominatim (recomenda-se um contato próprio) |
| `NOMINATIM_URL`, `OVERPASS_URLS`, `OSRM_BASE_URL` | instâncias públicas | Alternativas sem chave |
| `OVERPASS_TIMEOUT_SECONDS`, `OVERPASS_COOLDOWN_SECONDS` | `20`, `120` | Timeout por instância e pausa após falhas (circuit breaker) |
| `ANP_FUEL_BASE_URL`, `ANP_CACHE_TTL_SECONDS` | gov.br, `43200` | Origem e cache dos preços da ANP |
| `BCB_PTAX_URL` | API Olinda do BC | Endpoint da PTAX |
| `OPEN_METEO_FORECAST_URL`, `OPEN_METEO_ARCHIVE_URL`, `OPEN_METEO_GEOCODING_URL` | Open-Meteo | Endpoints de clima |
