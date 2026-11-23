"""Textos das tools de clima."""


class Tools:
    GET_FORECAST = (
        "Previsão diária (condição, temperaturas, chuva, vento, UV) para um intervalo de datas."
    )
    GET_WEATHER_BY_DATE = (
        "Previsão para uma data específica, se estiver dentro do horizonte de previsão."
    )
    GET_CLIMATE_NORMALS = (
        "Como o tempo costuma ser num período do ano (para viagens além do horizonte da "
        "previsão): médias de temperatura máxima e mínima, extremos, chuva por dia, chance de "
        "dia chuvoso, horas de sol e vento, calculadas com o histórico das mesmas datas nos "
        "últimos anos (Open-Meteo, reanálise ERA5)."
    )
    GET_SUN_TIMES = (
        "Nascer e pôr do sol, crepúsculo civil, hora dourada e duração do dia para qualquer "
        "data, no fuso horário do lugar. Útil para mirantes, trilhas, praias e fotos."
    )


class Params:
    LOCATION = "Cidade em texto, ex.: 'Campos do Jordão, SP'. Ou use coordinates."
    START_DATE = "Data inicial (YYYY-MM-DD)"
    END_DATE = "Data final (YYYY-MM-DD)"
    TARGET_DATE = "Data (YYYY-MM-DD)"
    CLIMATE_START = "Início do período (YYYY-MM-DD; o ano é ignorado, vale dia e mês)"
    CLIMATE_END = "Fim do período (até 31 dias depois do início)"
    CLIMATE_YEARS = "Quantos anos de histórico considerar (3 a 30)"
    SUN_END_DATE = "Data final opcional (até 31 dias); se omitida, só start_date"


class Fields:
    CLIMATE_PERIOD = "Período do ano analisado (dia/mês)"
    CLIMATE_YEARS = "Anos do histórico usados"
    RAINY_DAYS = "Percentual de dias com chuva >= 1 mm no período"
    CIVIL_TWILIGHT = "Crepúsculo civil: ainda há claridade para atividades ao ar livre"
    GOLDEN_HOUR = "Hora dourada (sol abaixo de 6°): melhor luz para fotos"


class Notes:
    LOW_CONFIDENCE = "Previsões com mais de 7 dias de antecedência têm baixa confiabilidade."
    UNAVAILABLE_DATES = (
        "Sem previsão para {count} data(s): fora do horizonte de {max_days} dias ou no passado. "
        "Use get_climate_normals para ver como o tempo costuma ser nessas datas."
    )
    CLIMATE_METHOD = (
        "Médias das mesmas datas em {count} anos de histórico; indicam o padrão do período, "
        "não uma previsão."
    )
    SUN_METHOD = "Horários calculados astronomicamente (precisão de ~1 minuto), sem relevo."


class Errors:
    MISSING_LOCATION = "Informe 'location' ou 'coordinates'."
    END_BEFORE_START = "end_date deve ser >= start_date."
    RANGE_TOO_LONG = "Intervalo máximo de 31 dias."
    NO_HISTORY = "Não há histórico disponível para esse período."


SUN_SOURCE = "cálculo astronômico (NOAA)"


UNKNOWN_CONDITION = "desconhecido"

# Códigos de tempo WMO -> descrição em português
CONDITIONS: dict[int, str] = {
    0: "céu limpo",
    1: "predominantemente limpo",
    2: "parcialmente nublado",
    3: "nublado",
    45: "nevoeiro",
    48: "nevoeiro com geada",
    51: "garoa fraca",
    53: "garoa moderada",
    55: "garoa intensa",
    56: "garoa congelante fraca",
    57: "garoa congelante intensa",
    61: "chuva fraca",
    63: "chuva moderada",
    65: "chuva forte",
    66: "chuva congelante fraca",
    67: "chuva congelante forte",
    71: "neve fraca",
    73: "neve moderada",
    75: "neve forte",
    77: "grãos de neve",
    80: "pancadas de chuva fracas",
    81: "pancadas de chuva moderadas",
    82: "pancadas de chuva fortes",
    85: "pancadas de neve fracas",
    86: "pancadas de neve fortes",
    95: "trovoadas",
    96: "trovoadas com granizo fraco",
    99: "trovoadas com granizo forte",
}
