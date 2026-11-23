"""Textos das tools de clima."""


class Tools:
    GET_FORECAST = (
        "Previsão diária (condição, temperaturas, chuva, vento, UV) para um intervalo de datas."
    )
    GET_WEATHER_BY_DATE = (
        "Previsão para uma data específica, se estiver dentro do horizonte de previsão."
    )


class Params:
    LOCATION = "Cidade em texto, ex.: 'Campos do Jordão, SP'. Ou use coordinates."
    START_DATE = "Data inicial (YYYY-MM-DD)"
    END_DATE = "Data final (YYYY-MM-DD)"
    TARGET_DATE = "Data (YYYY-MM-DD)"


class Notes:
    LOW_CONFIDENCE = "Previsões com mais de 7 dias de antecedência têm baixa confiabilidade."
    UNAVAILABLE_DATES = (
        "Sem previsão para {count} data(s): fora do horizonte de {max_days} dias ou no passado. "
        "Planeje com alternativas indoor."
    )


class Errors:
    MISSING_LOCATION = "Informe 'location' ou 'coordinates'."
    END_BEFORE_START = "end_date deve ser >= start_date."
    RANGE_TOO_LONG = "Intervalo máximo de 31 dias."


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
