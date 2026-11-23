"""Textos das tools de mapas."""


class Tools:
    CALCULATE_DISTANCE = (
        "Calcula a distância em linha reta (km) entre dois pontos. Rápido e sem provedor externo."
    )
    GET_ROUTE = (
        "Rota entre dois pontos (coordenadas, endereço ou place_id): distância, duração com "
        "trânsito para o horário de saída, duração sem trânsito, estradas principais, avisos e "
        "pedágios com custo estimado em R$ (Google Maps). Pode trazer rotas alternativas e "
        "evitar pedágios ou rodovias. Sem a chave do Google, usa OSRM (sem trânsito e sem pedágio)."
    )
    ESTIMATE_TOLL_COSTS = (
        "Estima o custo de pedágios entre origem e destino (ida, ou ida e volta) com as tarifas "
        "conhecidas pelo Google Maps para carro de passeio. Requer Google Maps."
    )
    GET_TRAVEL_TIME = (
        "Matriz de tempos e distâncias entre várias origens e destinos, com trânsito para o "
        "horário de saída (Google Maps). Útil para agrupar lugares próximos no mesmo dia."
    )
    OPTIMIZE_STOPS = (
        "Sugere a melhor ordem para visitar várias paradas, partindo da primeira (e terminando "
        "na última, ou voltando ao início), com a duração de cada trecho."
    )


class Params:
    TRAVEL_MODE = "Meio de transporte (transit = transporte público, só com Google)"
    WAYPOINT = "Ponto: informe coordinates, address OU place_id"
    DEPARTURE_TIME = (
        "Horário de saída para considerar o trânsito, ex.: '2026-12-12T08:00' (sem fuso = "
        "horário de Brasília). Precisa estar no futuro; se omitido, considera agora."
    )
    ALTERNATIVES = "Incluir rotas alternativas"
    AVOID_TOLLS = "Evitar pedágios"
    AVOID_HIGHWAYS = "Evitar rodovias"
    INCLUDE_POLYLINE = "Incluir o traçado da rota (polyline codificada)"
    TOLL_ROUND_TRIP = "Calcular ida e volta (a volta é calculada separadamente)"
    STOPS = "Paradas (2 a 12); a primeira é o ponto de partida"
    ROUNDTRIP = "Voltar ao ponto inicial no fim"


class Fields:
    DURATIONS = "durations_seconds[i][j] = origem i -> destino j (com trânsito, quando Google)"
    ORDER = "Índices das paradas de entrada na ordem sugerida"
    DURATION = "Duração estimada em segundos (com trânsito, quando traffic_aware=true)"
    STATIC_DURATION = "Duração sem considerar trânsito, em segundos"
    ROUTE_DESCRIPTION = "Resumo da rota (ex.: principais rodovias)"
    ROUTES = "Rota principal primeiro; alternativas em seguida"
    HAS_TOLLS = "true se a rota tem pedágio; null se desconhecido"
    TOLL_PRICE = "Custo estimado dos pedágios do trecho; null se o Google não souber a tarifa"
    TOLL_TOTAL = "Total estimado (ida e volta, se pedido); null se alguma tarifa for desconhecida"


class Notes:
    STRAIGHT_LINE = "Distância em linha reta; use get_route para distância viária."
    TRAFFIC_AWARE = "Duração considera o trânsito previsto pelo Google Maps."
    DEPARTURE_NOW = "Sem horário de saída: trânsito considerado para agora."
    NO_GOOGLE_KEY = (
        "Google Maps não configurado (GOOGLE_MAPS_API_KEY): usando OSRM como alternativa."
    )
    GOOGLE_FAILED = "Google Maps falhou ({error}); usando OSRM como alternativa."
    OSRM_LIMITS = "OSRM não considera trânsito nem informa pedágios."
    TOLL_PRICE_UNKNOWN = (
        "Há pedágio em algum trecho, mas o Google não informou a tarifa; o total não foi calculado."
    )
    TOLL_ESTIMATE_DISCLAIMER = (
        "Valores estimados pelo Google Maps para carro de passeio; tarifas podem mudar."
    )


class Errors:
    ROUTE_NOT_FOUND = "OSRM não encontrou rota ({code})."
    UNKNOWN_CODE = "erro desconhecido"
    GOOGLE_ROUTE_NOT_FOUND = "O Google Maps não encontrou rota entre os pontos informados."
    DEPARTURE_IN_PAST = "departure_time precisa estar no futuro."
    OSM_ID_IN_GOOGLE_ROUTE = (
        "IDs do OpenStreetMap (osm:...) não valem para o Google: use coordinates ou address."
    )
    GOOGLE_PLACE_ID_NEEDS_KEY = (
        "place_id do Google só pode ser usado com Google Maps configurado; use coordinates."
    )
    TRANSIT_NEEDS_GOOGLE = "Transporte público (transit) só está disponível com Google Maps."
    TOLLS_NEED_GOOGLE = (
        "Estimativa de pedágios requer Google Maps. Configure GOOGLE_MAPS_API_KEY no .env."
    )
