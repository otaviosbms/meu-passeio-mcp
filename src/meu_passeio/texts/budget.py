"""Textos das tools de custos e orçamento."""

DISCLAIMER = (
    "Estimativa calculada a partir dos valores informados e das fontes indicadas; "
    "preços reais podem variar."
)
FUEL_FORMULA = "(distance_km × (2 se ida e volta)) / consumo × preço_litro"

# Nível geográfico do preço de combustível
LEVELS = {"municipality": "do município", "state": "médio do estado", "national": "médio do Brasil"}


class Tools:
    CONVERT_CURRENCY = (
        "Converte valores entre moedas com a PTAX do Banco Central (taxa oficial de referência, "
        "boletim de fechamento mais recente até a data). Útil para viagens internacionais e "
        "preços em moeda estrangeira. Casas de câmbio e cartões cobram spread e IOF além da PTAX."
    )
    GET_FUEL_PRICE = (
        "Preço atual de combustível (gasolina, gasolina aditivada, etanol, diesel, diesel S10 "
        "ou GNV) na cidade, pela pesquisa semanal da ANP: média, mediana, mínimo e máximo dos "
        "postos pesquisados nas últimas 2 semanas. Se a cidade não estiver na pesquisa, usa a "
        "média do estado e avisa."
    )
    CALCULATE_FUEL_COST = (
        "Estima o custo de combustível de um trajeto a partir da distância e do consumo do "
        "veículo. Se o preço do litro não for informado, usa o preço médio atual da ANP na "
        "cidade/estado de abastecimento."
    )
    ESTIMATE_MEAL_COST = (
        "Estima quanto custa uma refeição por pessoa na região (café da manhã, almoço, jantar, "
        "lanche ou refeição rápida) a partir da faixa de preço real dos estabelecimentos bem "
        "avaliados no Google Maps: mediana e faixa típica, com exemplos. Requer Google Maps."
    )
    ESTIMATE_TRIP_COST = (
        "Consolida custos (atividades, alimentação, deslocamentos, pedágios, hospedagem) e "
        "compara ao orçamento. Informe em cada item a fonte do valor (google_maps, anp, "
        "google_routes_tolls, user ou assumption): o resultado separa o que é dado real do que "
        "é suposição."
    )
    CALCULATE_BUDGET_BREAKDOWN = (
        "Distribui um orçamento por categorias e por dia, indicando valores por pessoa. É uma "
        "sugestão de divisão, não uma estimativa de preços."
    )


class Params:
    AMOUNT = "Valor a converter"
    FROM_CURRENCY = (
        "Moeda de origem (código ISO). PTAX: USD, EUR, GBP, JPY, CHF, CAD, AUD, DKK, NOK, SEK; "
        "ou BRL"
    )
    TO_CURRENCY = "Moeda de destino (padrão: BRL)"
    QUOTE_ON = "Data da cotação (YYYY-MM-DD); se omitida, a mais recente"
    DISTANCE_KM = "Distância de um trecho, em km"
    CONSUMPTION = "Consumo do veículo em km/l (padrão 12; ajuste para o carro real)"
    FUEL_PRICE = "Preço do litro em BRL; se omitido, usa o preço médio da ANP (informe state)"
    STATE = "UF, ex.: 'SP', 'PR'"
    CITY = "Município, ex.: 'Marília' (acentos opcionais)"
    FUEL = "Combustível"
    MEAL = (
        "Refeição: breakfast (café da manhã), lunch (almoço), dinner (jantar), snack (lanche), "
        "quick (refeição rápida)"
    )
    LOCATION = "Cidade/bairro, ex.: 'Centro, Curitiba, PR'. Use isto OU coordinates."
    COORDINATES = "Ponto de referência. Use isto OU location."
    CUISINE = "Culinária opcional, ex.: 'italiana', 'japonesa'"
    RADIUS_KM = "Raio de busca em km"
    MIN_RATING = "Nota mínima dos estabelecimentos considerados"
    BUDGET = "Orçamento para comparar"
    WEIGHTS = "Pesos por categoria (padrão: food 40, activities 30, transport 20, contingency 10)"
    EXCLUDED_CATEGORIES = "Categorias a excluir"


class Fields:
    RATE = "Quantas unidades da moeda de destino por 1 unidade da moeda de origem"
    QUOTE_DATE = "Data do boletim PTAX usado"
    QUOTES = "R$ por unidade de cada moeda estrangeira envolvida (PTAX de venda)"
    CATEGORY = "ex.: activities, food, transport, tolls, fuel, accommodation"
    AMOUNT = "Valor unitário"
    PER_PERSON = "Multiplica pelo número de viajantes"
    ITEM_SOURCE = (
        "Origem do valor: google_maps, anp, google_routes_tolls, user (informado pelo usuário) "
        "ou assumption (suposição)"
    )
    ASSUMED_SHARE = "Fração do total (0 a 1) baseada em suposições, sem fonte real"
    PRICE_SOURCE = "Origem do preço do combustível: anp ou user"
    FUEL_LEVEL = "Abrangência do preço: municipality, state ou national"
    FUEL_STATIONS = "Número de preços coletados considerados (últimas 2 semanas)"
    MEAL_MEDIAN = "Mediana do custo por pessoa; null se não houver dados suficientes"
    MEAL_TYPICAL_RANGE = "Faixa típica (1º e 3º quartis) do custo por pessoa"


class Notes:
    PTAX_REFERENCE = (
        "PTAX de venda (Banco Central), referência oficial; o valor pago em casas de câmbio ou "
        "no cartão inclui spread e IOF."
    )
    FUTURE_DATE_USES_LATEST = "Data futura: usada a cotação mais recente disponível."
    CATEGORY_EXCLUDED = "Categoria '{category}' excluída do orçamento."
    ANP_SOURCE = "Fonte: ANP — Levantamento de Preços de Combustíveis (dados abertos)."
    ANP_CITY_NOT_SURVEYED = "{city} não está na pesquisa da ANP; usado o preço {level}."
    FUEL_PRICE_FROM_ANP = "Preço médio da ANP: R$ {price} ({level}, coletas de {start} a {end})."
    CONSUMPTION_ASSUMPTION = (
        "Consumo considerado: {km_l} km/l; ajuste para o veículo real se souber."
    )
    MEAL_METHOD = (
        "Calculado pela mediana do ponto médio das faixas de preço por pessoa informadas no "
        "Google Maps; bebidas e gorjeta podem não estar incluídas."
    )
    MEAL_INSUFFICIENT = (
        "Só {count} estabelecimento(s) com faixa de preço no Google: dados insuficientes para "
        "estimar. Veja price_level_counts e os exemplos."
    )
    HIGH_ASSUMED_SHARE = (
        "{pct}% do total vem de suposições (source=assumption): trate o total como aproximado."
    )


class Errors:
    SAME_CURRENCY = "from_currency e to_currency são iguais."
    UNKNOWN_CURRENCY = "Moeda '{currency}' não disponível na PTAX. Disponíveis: {available}, BRL."
    NO_QUOTE = "Sem cotação PTAX para {currency} até {date}."
    NEGATIVE_DISTANCE = "distance_km deve ser >= 0"
    INVALID_CONSUMPTION = "consumption_km_per_liter deve ser > 0"
    NEGATIVE_FUEL_PRICE = "fuel_price_per_liter deve ser >= 0"
    INVALID_TRAVELERS = "travelers deve ser >= 1"
    NEGATIVE_BUDGET = "total_budget deve ser >= 0"
    INVALID_DAYS_OR_TRAVELERS = "days e travelers devem ser >= 1"
    INVALID_WEIGHTS = "weights deve ter ao menos uma categoria com peso > 0"
    FUEL_PRICE_OR_STATE = (
        "Informe fuel_price_per_liter ou state (e opcionalmente city) para usar o preço da ANP."
    )
    ANP_EMPTY = "O arquivo da ANP veio vazio ou em formato inesperado."
    FUEL_NOT_FOUND = "Sem preços da ANP para o combustível '{fuel}'."
    MEAL_NEEDS_GOOGLE = (
        "Estimativa de refeição requer Google Maps. Configure GOOGLE_MAPS_API_KEY no .env."
    )
