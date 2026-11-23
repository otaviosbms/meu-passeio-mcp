"""Textos das tools de lugares."""


class Tools:
    SEARCH_PLACES = (
        "Busca lugares por categoria e/ou texto em torno de uma cidade ou coordenada.\n\n"
        "Retorna nome, categoria, endereço, coordenadas, distância do centro e horário de "
        "funcionamento (texto bruto do OSM, quando existir). Resultados ordenados por distância."
    )
    SEARCH_RESTAURANTS = "Busca restaurantes, cafés, bares e outras opções de alimentação próximas."
    GET_PLACE_DETAILS = (
        "Obtém detalhes de um lugar: horário bruto, site, telefone, acessibilidade e tags úteis."
    )


class Params:
    LOCATION = "Cidade/região em texto, ex.: 'Curitiba, PR, Brasil'. Use isto OU coordinates."
    COORDINATES = "Centro da busca. Use isto OU location."
    RADIUS_KM = "Raio de busca em km"
    LIMIT = "Máximo de resultados"
    CATEGORIES = "Categorias de lugar. Se omitido, usa 'query' como busca textual."
    QUERY = "Texto livre (busca por nome/termo) ou filtro de nome quando há categorias"
    FOOD_TYPES = "Tipos de estabelecimento (padrão: restaurant)"
    CUISINE = "Filtro de culinária do OSM, ex.: 'italian', 'pizza', 'japanese'"
    PLACE_ID = "ID retornado pelas buscas, ex.: osm:node:123"


class Fields:
    ID = "ID de origem no formato osm:<tipo>:<id>"
    DISTANCE_KM = "Distância em linha reta do centro"
    RATING = "OSM não fornece avaliações: null"
    OPENING_HOURS = "Texto bruto do provedor"
    TAGS = "Tags brutas relevantes do OSM"


class Notes:
    NO_PLACES = "Nenhum lugar encontrado; tente aumentar o raio ou mudar as categorias."
    NO_RESTAURANTS = "Nenhum estabelecimento encontrado com esses filtros."


class Errors:
    MISSING_SEARCH = "Informe 'categories' e/ou 'query'."
    MISSING_LOCATION = "Informe 'location' (texto) ou 'coordinates'."
    NO_VALID_CATEGORY = "Nenhuma categoria válida informada."
    OVERPASS_CIRCUIT_OPEN = "Overpass temporariamente indisponível (circuit breaker aberto)."
    OVERPASS_NOT_CONFIGURED = "Nenhuma instância Overpass configurada."
    INVALID_PLACE_ID = "place_id inválido. Formato esperado: osm:<node|way|relation>:<id>"
    PLACE_NOT_FOUND = "Lugar não encontrado: {place_id}"
    PLACE_WITHOUT_NAME = "Lugar sem nome no provedor: {place_id}"


class Sources:
    OSM = "openstreetmap"
    NOMINATIM_FALLBACK = "openstreetmap (nominatim fallback)"
