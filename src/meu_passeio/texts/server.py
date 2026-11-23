"""Textos do MCP Server único do Meu Passeio (instruções gerais e prompts)."""

NAME = "meu-passeio"
TITLE = "Meu Passeio"

INSTRUCTIONS = """\
Meu Passeio é um planejador de viagens: de um bate-volta a férias com várias cidades.
As tools cobrem cinco áreas e foram feitas para serem combinadas:

- Lugares (search_places, search_restaurants, get_place_details, check_opening_hours,
  find_nearby, search_along_route): via Google Maps, com nota, número de avaliações,
  nível/faixa de preço e horários. Sem a chave do Google, cai para OpenStreetMap (sem
  avaliações nem preços) e o resultado avisa em `notes`. Preserve os IDs e as coordenadas.
- Mapas (calculate_distance, get_route, estimate_toll_costs, get_travel_time,
  optimize_stops): rotas do Google Maps com trânsito para o horário de saída e pedágios em
  R$. Sem a chave, usa OSRM (sem trânsito e sem pedágio).
- Clima (get_forecast, get_weather_by_date): previsão diária via Open-Meteo, até
  {max_days} dias à frente. Para datas mais distantes não há previsão: comunique a incerteza.
- Custos (get_fuel_price, calculate_fuel_cost, estimate_meal_cost, estimate_trip_cost,
  calculate_budget_breakdown): preço real de combustível pela ANP, custo de refeição pela
  faixa de preço dos restaurantes no Google e consolidação com a fonte de cada valor.
- Planejamento (suggest_day_trip_destinations, optimize_day_itinerary): destinos de
  bate-volta dentro de um tempo de carro e agenda do dia com horários e funcionamento.

Fluxo sugerido para montar um roteiro:
1. Sem destino definido (ex.: "bate-volta até 2h de carro"), comece por
   suggest_day_trip_destinations.
2. Busque lugares que combinem com as preferências. Prefira os bem avaliados e com muitas
   avaliações (use min_rating e min_reviews); evite lugares com poucas notas.
3. Para cada dia, monte a agenda com optimize_day_itinerary usando os place_id do Google:
   ela ordena as paradas, calcula horários e confere se cada lugar estará aberto.
4. Para refeições, use search_restaurants ou find_nearby perto das atrações do dia.
5. Consulte o clima nas datas para priorizar atividades ao ar livre ou alternativas indoor.
6. Custos com fontes reais: combustível com calculate_fuel_cost (preço da ANP na cidade de
   abastecimento; pergunte o consumo do carro se não souber), pedágios com
   estimate_toll_costs, refeições com estimate_meal_cost. Consolide em estimate_trip_cost
   informando a fonte de cada item; o que não vier de uma tool é source=assumption e deve
   ser apresentado como suposição.

Não invente lugares, horários de funcionamento, avaliações ou preços: use só o que as
tools retornarem e deixe claro o que é estimativa. Ao apresentar dados do Google, cite
"Google Maps" como fonte e, em avaliações, o nome do autor.
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
