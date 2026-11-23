"""Textos do MCP Server único do Meu Passeio (instruções gerais e prompts)."""

NAME = "meu-passeio"
TITLE = "Meu Passeio"

INSTRUCTIONS = """\
Meu Passeio é um planejador de viagens: de um bate-volta a férias com várias cidades.
As tools cobrem quatro áreas e foram feitas para serem combinadas:

- Lugares (search_places, search_restaurants, get_place_details): atrações, natureza,
  cultura e alimentação via OpenStreetMap. Avaliações não existem neste provedor
  (rating=null). Preserve os IDs (osm:<tipo>:<id>) e as coordenadas retornadas.
- Mapas (calculate_distance, get_route, get_travel_time, optimize_stops): distâncias,
  rotas e tempos via OSRM. As durações NÃO consideram trânsito em tempo real.
- Clima (get_forecast, get_weather_by_date): previsão diária via Open-Meteo, até
  {max_days} dias à frente. Para datas mais distantes não há previsão: comunique a incerteza.
- Orçamento (calculate_fuel_cost, estimate_trip_cost, calculate_budget_breakdown):
  cálculos determinísticos. Os resultados são estimativas, nunca preços reais.

Fluxo sugerido para montar um roteiro:
1. Busque lugares que combinem com as preferências no destino.
2. Use mapas para agrupar lugares próximos no mesmo dia e checar os deslocamentos.
3. Consulte o clima nas datas para priorizar atividades ao ar livre ou alternativas indoor.
4. Feche o orçamento com as tools de orçamento.

Não invente lugares, horários de funcionamento, avaliações ou preços: use só o que as
tools retornarem e deixe claro o que é estimativa.
"""


class Prompts:
    PLAN_TRIP_TITLE = "Planejar viagem"
    PLAN_TRIP_DESCRIPTION = (
        "Monta um roteiro de viagem usando as tools do Meu Passeio "
        "(lugares, mapas, clima e orçamento)."
    )

    class Args:
        DESTINATION = "Destino da viagem, ex.: 'Campos do Jordão, SP'"
        DAYS = "Duração ou datas, ex.: '4 dias' ou '10 a 13 de julho'"
        ORIGIN = "Cidade de partida (opcional)"
        TRAVELERS = "Número de pessoas (opcional)"
        BUDGET = "Orçamento e o que ele inclui (opcional), ex.: 'R$ 1.800 sem hospedagem'"
        PREFERENCES = "Interesses (opcional), ex.: 'natureza, restaurantes, passeios românticos'"

    PLAN_TRIP_TEMPLATE = """\
Planeje uma viagem com as tools do Meu Passeio.

- Destino: {destination}
- Duração/datas: {days}
- Origem: {origin}
- Pessoas: {travelers}
- Orçamento: {budget}
- Preferências: {preferences}

Siga o fluxo: lugares que combinem com as preferências → agrupamento por proximidade e
tempos de deslocamento → previsão do tempo nas datas → orçamento estimado.

Entregue um roteiro por dia (horários sugeridos, lugares com endereço e distância entre
eles), o resumo do clima, a estimativa de custos com as premissas usadas e as observações
sobre dados ausentes ou incertos.
"""
    NOT_INFORMED = "não informado"
