"""Textos das tools de orçamento."""

DISCLAIMER = "Estimativa calculada a partir dos parâmetros informados; não é um preço real."
FUEL_FORMULA = "(distance_km × (2 se ida e volta)) / consumo × preço_litro"


class Tools:
    CALCULATE_FUEL_COST = (
        "Estima o custo de combustível a partir de distância, consumo do veículo e preço do litro."
    )
    ESTIMATE_TRIP_COST = (
        "Consolida custos (atividades, alimentação, deslocamentos, hospedagem) e compara ao "
        "orçamento."
    )
    CALCULATE_BUDGET_BREAKDOWN = (
        "Distribui um orçamento por categorias e por dia, indicando valores por pessoa."
    )


class Params:
    DISTANCE_KM = "Distância de um trecho, em km"
    FUEL_PRICE = "Preço do litro em BRL"
    BUDGET = "Orçamento para comparar"
    WEIGHTS = "Pesos por categoria (padrão: food 40, activities 30, transport 20, contingency 10)"
    EXCLUDED_CATEGORIES = "Categorias a excluir"


class Fields:
    CATEGORY = "ex.: activities, food, transport, accommodation, tolls"
    AMOUNT = "Valor unitário estimado"
    PER_PERSON = "Multiplica pelo número de viajantes"


class Notes:
    CATEGORY_EXCLUDED = "Categoria '{category}' excluída do orçamento."


class Errors:
    NEGATIVE_DISTANCE = "distance_km deve ser >= 0"
    INVALID_CONSUMPTION = "consumption_km_per_liter deve ser > 0"
    NEGATIVE_FUEL_PRICE = "fuel_price_per_liter deve ser >= 0"
    INVALID_TRAVELERS = "travelers deve ser >= 1"
    NEGATIVE_BUDGET = "total_budget deve ser >= 0"
    INVALID_DAYS_OR_TRAVELERS = "days e travelers devem ser >= 1"
    INVALID_WEIGHTS = "weights deve ter ao menos uma categoria com peso > 0"
