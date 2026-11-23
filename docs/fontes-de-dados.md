# Fontes de dados

[← Voltar ao README](../README.md)

| Fonte | Usada para | Chave |
|---|---|---|
| [Google Places API (New)](https://developers.google.com/maps/documentation/places/web-service/op-overview) | Lugares, notas, preços, horários, avaliações | Sim |
| [Google Routes API](https://developers.google.com/maps/documentation/routes) | Rotas com trânsito, pedágios, matriz de tempos, ordem de paradas | Sim |
| [Open-Meteo](https://open-meteo.com/) | Previsão, histórico (ERA5) e fuso horário do local | Não |
| [ANP — dados abertos](https://www.gov.br/anp/pt-br/centrais-de-conteudo/dados-abertos/serie-historica-de-precos-de-combustiveis) | Preço de combustível por município | Não |
| [Banco Central — PTAX](https://dadosabertos.bcb.gov.br/) | Câmbio oficial de fechamento | Não |
| [OpenStreetMap](https://www.openstreetmap.org/) (Nominatim + Overpass) e [OSRM](https://routing.openstreetmap.de/) | Geocodificação e alternativa sem chave para lugares e rotas | Não |
| Cálculo local | Nascer/pôr do sol e feriados nacionais | — |

## Detalhes por fonte

**Google Maps.** As chamadas pedem só os campos necessários (`X-Goog-FieldMask`). Ao exibir
dados do Google, cite "Google Maps" como fonte — as tools devolvem `attribution`. Configuração
e custos em [Chave do Google Maps](google-maps.md).

**OpenStreetMap/OSRM.** Alternativa quando não há chave do Google ou ele falha. O OSM não tem
avaliações nem preços; o OSRM não considera trânsito nem pedágios. As instâncias públicas do
Overpass oscilam, então há failover entre instâncias, circuit breaker e, por último, busca no
Nominatim.

**Open-Meteo.** Previsão diária até 16 dias à frente. Para datas mais distantes,
`get_climate_normals` usa o histórico (reanálise ERA5) das mesmas datas nos últimos anos.

**ANP.** Arquivo "últimas 4 semanas" da série histórica de preços (preço de venda por posto).
As tools usam as coletas das últimas 2 semanas antes da mais recente. A pesquisa cobre cerca de
400 municípios; para os demais, usa a média do estado (ou do Brasil) e avisa. O arquivo fica em
cache por 12 horas.

**PTAX.** Taxa de referência do Banco Central, boletim de fechamento mais recente até a data
pedida. Cobre 10 moedas; conversão entre duas estrangeiras passa pelo real. Casas de câmbio e
cartões cobram spread e IOF além da PTAX.

**Cálculo local.**
- *Sol:* algoritmo de posição solar da NOAA, com precisão de cerca de 1 minuto, convertido para
  o fuso do lugar (considera horário de verão).
- *Feriados:* datas fixas das leis federais e datas móveis a partir da Páscoa; Consciência Negra
  como feriado nacional desde 2024. Feriados estaduais e municipais não estão incluídos.
