"""Textos das tools de mapas."""


class Tools:
    CALCULATE_DISTANCE = (
        "Calcula a distância em linha reta (km) entre dois pontos. Rápido e sem provedor externo."
    )
    GET_ROUTE = "Obtém a rota viária entre dois pontos: distância (m) e duração estimada (s)."
    GET_TRAVEL_TIME = (
        "Estima tempos de deslocamento entre vários locais (matriz origens x destinos)."
    )
    OPTIMIZE_STOPS = (
        "Sugere uma ordem eficiente para visitar várias paradas (problema do caixeiro viajante)."
    )


class Params:
    TRAVEL_MODE = "Meio de transporte"
    INCLUDE_POLYLINE = "Incluir polyline simplificada"
    STOPS = "Paradas; a primeira é o ponto de partida"
    ROUNDTRIP = "Voltar ao ponto inicial no fim"


class Fields:
    DURATIONS = "durations_seconds[i][j] = origem i -> destino j"
    ORDER = "Índices das paradas de entrada na ordem sugerida"


class Notes:
    STRAIGHT_LINE = "Distância em linha reta; use get_route para distância viária."


class Errors:
    ROUTE_NOT_FOUND = "OSRM não encontrou rota ({code})."
    UNKNOWN_CODE = "erro desconhecido"
