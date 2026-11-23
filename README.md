# Meu Passeio

**MCP Server (Model Context Protocol) de planejamento de viagens** — de um bate-volta a férias
com várias cidades. Um único server expõe **28 tools** de lugares, rotas, clima, custos,
planejamento e roteiros salvos, além do prompt `planejar_viagem`, para qualquer cliente MCP
(Claude Desktop, Claude Code etc.).

> "Quero um bate-volta saindo de Marília, até 2 horas de carro, com natureza e orçamento de R$ 400."

O projeto **não tem IA interna**: quem planeja é o cliente MCP, combinando as tools. O server
entrega dados reais e verificáveis e marca o que é estimativa:

- lugares com nota, número de avaliações, faixa de preço e horários (Google Maps);
- rotas com trânsito e pedágios em R$, e agenda do dia com horário de funcionamento;
- preço de combustível da ANP, custo de refeição pela faixa de preço dos restaurantes e câmbio
  oficial do Banco Central;
- previsão do tempo, médias históricas para datas distantes, nascer e pôr do sol e feriados.

Sem a chave do Google, lugares e rotas usam OpenStreetMap/OSRM como alternativa gratuita.

**Stack:** Python 3.11+ · MCP Python SDK 2.x · FastAPI · SQLAlchemy · Google Maps Platform ·
Open-Meteo · ANP · Banco Central (PTAX) · OpenStreetMap/OSRM.

## Início rápido

```powershell
git clone https://github.com/otaviosbms/meu-passeio-mcp.git
cd meu-passeio-mcp
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env   # opcional: preencha GOOGLE_MAPS_API_KEY
```

No Claude Desktop, adicione ao `claude_desktop_config.json` e reinicie o app:

```json
{
  "mcpServers": {
    "meu-passeio": {
      "command": "C:\\caminho\\meu-passeio-mcp\\.venv\\Scripts\\python.exe",
      "args": ["-m", "meu_passeio.mcp_server"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

## Documentação

| Documento | Conteúdo |
|---|---|
| [Instalação e Claude Desktop](docs/instalacao.md) | Instalação, configuração no Claude Desktop e solução de problemas |
| [Chave do Google Maps](docs/google-maps.md) | Como obter e restringir a chave, e como controlar custos |
| [Tools](docs/tools.md) | As 28 tools por área, o prompt `planejar_viagem` e o fluxo sugerido |
| [Fontes de dados](docs/fontes-de-dados.md) | Google, Open-Meteo, ANP, PTAX, OSM/OSRM e cálculos locais |
| [Arquitetura](docs/arquitetura.md) | Visão geral, princípios e estrutura do projeto |
| [API HTTP](docs/api.md) | Endpoints da API FastAPI, Docker e configuração do MCP Client |
| [Configuração](docs/configuracao.md) | Variáveis de ambiente |
| [Desenvolvimento](docs/desenvolvimento.md) | Testes, lint e como adicionar uma tool |
| [Segurança e limites](docs/seguranca.md) | Chaves, validação, erros, resiliência e logs |
| [Roadmap](docs/roadmap.md) | O que já foi feito e próximos passos |
