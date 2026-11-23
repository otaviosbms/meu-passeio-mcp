# Tools

[← Voltar ao README](../README.md)

O server `meu-passeio` expõe 28 tools em seis áreas, além do prompt `planejar_viagem`.
Tools marcadas com *Requer Google* precisam da [chave do Google Maps](google-maps.md).

## Lugares — `places`

| Tool | O que faz |
|---|---|
| `search_places` | Atrações, natureza, cultura, compras e alimentação perto de uma cidade ou coordenada. Com Google: nota, nº de avaliações, nível e faixa de preço, aberto agora, link do Maps. Filtros `min_rating`, `min_reviews`, `open_now`, `price_levels`; ordena por qualidade (nota ponderada pelo nº de avaliações), distância ou popularidade. |
| `search_restaurants` | Restaurantes, cafés, bares, padarias e sorveterias, com filtro de culinária e faixa de preço por pessoa. |
| `get_place_details` | Horários de cada dia, resumo, telefone, site, até 5 avaliações, acessibilidade, estacionamento, pagamento e comodidades. |
| `check_opening_hours` | Diz se o lugar estará aberto numa data e hora; nos próximos 7 dias considera feriados e horários especiais. |
| `find_nearby` | O que há perto de um lugar escolhido (ex.: restaurante bem avaliado a 500 m do museu). |
| `search_along_route` | Paradas ao longo do trajeto (postos, restaurantes, mirantes). *Requer Google.* |

## Rotas — `maps`

| Tool | O que faz |
|---|---|
| `calculate_distance` | Distância em linha reta entre dois pontos (local, sem API). |
| `get_route` | Rota por coordenadas, endereço ou `place_id`: duração com e sem trânsito, rodovias, avisos, pedágios em R$, alternativas, evitar pedágios/rodovias; modos carro, a pé, bicicleta e transporte público (este só com Google). |
| `estimate_toll_costs` | Pedágios de ida, ou ida e volta, com as tarifas conhecidas pelo Google. *Requer Google.* |
| `get_travel_time` | Matriz de tempos e distâncias entre várias origens e destinos, com trânsito. |
| `optimize_stops` | Melhor ordem para várias paradas, com a duração de cada trecho. |

## Clima — `weather`

| Tool | O que faz |
|---|---|
| `get_forecast` | Previsão diária (condição, temperaturas, chuva, vento, UV) até 16 dias. |
| `get_weather_by_date` | Previsão para uma data específica. |
| `get_climate_normals` | Como o tempo costuma ser num período do ano: médias das mesmas datas nos últimos 10 anos (3 a 30), com chance de dia chuvoso, extremos e horas de sol. Para viagens além da previsão. |
| `get_sun_times` | Nascer e pôr do sol, crepúsculo, hora dourada e duração do dia para qualquer data, no fuso do lugar. |

## Custos — `budget`

| Tool | O que faz |
|---|---|
| `get_fuel_price` | Preço de gasolina, aditivada, etanol, diesel, diesel S10 ou GNV na cidade, pela pesquisa da ANP (média, mediana, mínimo e máximo das últimas 2 semanas). Cidade fora da pesquisa usa a média do estado. |
| `calculate_fuel_cost` | Custo de combustível de um trajeto; sem preço informado, usa o da ANP na cidade de abastecimento. |
| `estimate_meal_cost` | Custo por pessoa de café da manhã, almoço, jantar, lanche ou refeição rápida, pela faixa de preço real dos estabelecimentos bem avaliados. *Requer Google.* |
| `convert_currency` | Câmbio oficial pela PTAX do Banco Central (USD, EUR, GBP, JPY, CHF, CAD, AUD, DKK, NOK, SEK), com taxa cruzada via real. |
| `estimate_trip_cost` | Consolida custos informando a fonte de cada item (`google_maps`, `anp`, `google_routes_tolls`, `user`, `assumption`) e mostra quanto do total é suposição. |
| `calculate_budget_breakdown` | Sugere a divisão de um orçamento por categoria e por dia. |

## Planejamento — `planning`

| Tool | O que faz |
|---|---|
| `suggest_day_trip_destinations` | Destinos de bate-volta até X horas de carro: atrações bem avaliadas agrupadas por município, com o tempo real de viagem (com trânsito). *Requer Google.* |
| `optimize_day_itinerary` | Agenda do dia: ordena as paradas, calcula chegada e saída de cada uma e confere o horário de funcionamento (espera abrir, fechado, fecha antes do fim da visita). |
| `get_holidays` | Feriados nacionais e pontos facultativos num período, com fins de semana prolongados e emendas. Feriados estaduais e municipais não estão incluídos. |

## Roteiros — `trips`

| Tool | O que faz |
|---|---|
| `save_trip` | Salva um roteiro (`TripPlan`) e devolve o ID. |
| `list_trips` | Lista os roteiros salvos. |
| `get_trip` | Abre um roteiro pelo ID. |
| `update_trip` | Substitui o plano de um roteiro salvo. |

Os roteiros ficam no mesmo banco da API: um roteiro salvo pelo Claude aparece em `GET /trips`
(veja [API HTTP](api.md)).

## Prompt `planejar_viagem`

Modelo de pedido que aparece no cliente MCP, com os argumentos destino, dias, origem, pessoas,
orçamento e preferências. É só um texto pronto que orienta o fluxo de uso das tools.

## Fluxo sugerido

As instruções do server orientam o cliente a:

1. Sem destino definido, começar por `suggest_day_trip_destinations` e conferir feriados com
   `get_holidays`.
2. Buscar lugares bem avaliados e com muitas avaliações (`min_rating`, `min_reviews`).
3. Montar cada dia com `optimize_day_itinerary`, usando os `place_id` do Google.
4. Escolher refeições com `search_restaurants` ou `find_nearby` perto das atrações.
5. Usar a previsão nas datas próximas, `get_climate_normals` nas distantes e `get_sun_times`
   para mirantes, praias e trilhas.
6. Calcular custos com fontes reais (`calculate_fuel_cost`, `estimate_toll_costs`,
   `estimate_meal_cost`, `convert_currency`) e consolidar em `estimate_trip_cost`.
7. Oferecer salvar o roteiro aprovado com `save_trip`.
