"""Textos das tools de planejamento (bate-volta e agenda do dia)."""

UNNAMED_STOP = "Parada {n}"


class Tools:
    SUGGEST_DAY_TRIP_DESTINATIONS = (
        "Sugere destinos de bate-volta a partir de uma cidade de origem, até um tempo máximo de "
        "carro. Procura atrações bem avaliadas no Google Maps na região, agrupa por município e "
        "confirma o tempo real de viagem com trânsito. Retorna os municípios ordenados pela "
        "qualidade das atrações, com tempo de carro, distância e as melhores atrações de cada um. "
        "Requer Google Maps."
    )
    OPTIMIZE_DAY_ITINERARY = (
        "Monta a agenda de um dia: ordena as paradas para reduzir o deslocamento (ou mantém a "
        "ordem dada), calcula o horário de chegada e saída de cada uma a partir do horário de "
        "início e do tempo de visita, e confere se cada lugar estará aberto na chegada (para "
        "paradas com place_id do Google). Avisa quando é preciso esperar abrir, quando o lugar "
        "estará fechado ou fecha antes do fim da visita."
    )


class Params:
    MAX_DRIVE_HOURS = "Tempo máximo de carro (só ida), em horas, ex.: 2"
    ORIGIN = "Cidade de partida, ex.: 'Marília, SP'. Use isto OU origin_coordinates."
    ORIGIN_COORDINATES = "Coordenadas de partida. Use isto OU origin."
    INTERESTS = (
        "Tipos de atração de interesse (padrão: tourist_attraction, waterfall, viewpoint, park)"
    )
    MIN_RATING = "Nota mínima das atrações consideradas"
    MIN_REVIEWS = "Mínimo de avaliações das atrações consideradas"
    MIN_DISTANCE_KM = "Distância mínima em linha reta, para excluir a própria cidade de origem"
    DEPARTURE_TIME = (
        "Horário de saída para considerar o trânsito (sem fuso = horário de Brasília); "
        "precisa estar no futuro"
    )
    LIMIT = "Máximo de destinos"
    START = "Ponto de partida do dia (hotel, casa): coordinates, address OU place_id"
    END = "Ponto final do dia; se omitido, volta ao ponto de partida"
    STOPS = "Paradas do dia (até 10), cada uma com place, name e visit_minutes"
    STOP_PLACE = "Lugar: use place_id do Google para conferir o horário de funcionamento"
    STOP_NAME = "Nome para exibir (opcional; com place_id do Google é preenchido)"
    VISIT_MINUTES = "Tempo de permanência em minutos"
    DAY = "Data do passeio (YYYY-MM-DD)"
    START_TIME = "Horário de saída do ponto de partida, HH:MM (horário local)"
    TRAVEL_MODE = "Meio de transporte"
    KEEP_ORDER = "Manter a ordem das paradas como informada (não otimizar)"


class Fields:
    DRIVE_MINUTES = "Tempo de carro até a principal atração do município (com trânsito)"
    SCORE = "Soma da qualidade das 3 melhores atrações (nota ponderada pelo nº de avaliações)"
    INPUT_INDEX = "Posição da parada na lista de entrada"
    CLOCK = "Horário local HH:MM"
    END_ARRIVAL = "Horário de chegada ao ponto final"


class Notes:
    DAY_TRIP_METHOD = (
        "Tempos de carro calculados pelo Google Maps até a atração mais bem avaliada de cada "
        "município; atrações dentro do raio, filtradas por nota e número de avaliações."
    )
    NO_DAY_TRIPS = (
        "Nenhum destino encontrado; tente aumentar o tempo máximo, mudar os interesses ou "
        "reduzir min_rating/min_reviews."
    )
    TRAFFIC_AT_START = (
        "Trânsito considerado para o horário de saída; trechos mais tarde no dia podem variar."
    )
    NO_GOOGLE_KEY = (
        "Google Maps não configurado: deslocamentos pelo OSRM (sem trânsito) e sem conferência "
        "de horários de funcionamento."
    )
    GOOGLE_FAILED = "Google Maps falhou ({error}); deslocamentos calculados pelo OSRM."
    NO_HOURS_CHECK = (
        "Horários de funcionamento não conferidos (use place_id do Google nas paradas)."
    )


class Warnings:
    WAIT = "chega antes de abrir; espera {minutes} min (abre às {opens})"
    CLOSED = "fechado no horário de chegada (próxima abertura: {opens})"
    CLOSES_DURING_VISIT = "fecha às {closes}, antes do fim da visita"
    PAST_MIDNIGHT = "a agenda passa da meia-noite"


class Errors:
    GOOGLE_REQUIRED = (
        "Esta operação requer Google Maps. Configure GOOGLE_MAPS_API_KEY no .env do projeto."
    )
    ORIGIN_NOT_FOUND = "Não foi possível localizar a origem; informe origin_coordinates."
    INVALID_START_TIME = "start_time inválido; use HH:MM."
    TRANSIT_NEEDS_GOOGLE = "Transporte público (transit) só está disponível com Google Maps."
