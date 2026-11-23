"""Textos das tools de lugares."""

ATTRIBUTION = "Dados de lugares: Google Maps"
NEAR = "em"

# Dias da semana no padrão do Google (0 = domingo)
WEEKDAYS = ["domingo", "segunda", "terça", "quarta", "quinta", "sexta", "sábado"]


class Tools:
    SEARCH_PLACES = (
        "Busca lugares para visitar (atrações, natureza, cultura, compras, alimentação) em torno "
        "de uma cidade ou coordenada.\n\n"
        "Com Google Maps: retorna nota, número de avaliações, nível e faixa de preço, se está "
        "aberto agora, endereço, coordenadas e link do Google Maps. Filtros de nota mínima, "
        "mínimo de avaliações, aberto agora e faixa de preço. Por padrão ordena por qualidade "
        "(nota ponderada pelo número de avaliações). Sem a chave do Google, usa OpenStreetMap, "
        "que não tem avaliações nem preços."
    )
    SEARCH_RESTAURANTS = (
        "Busca restaurantes, cafés, bares, padarias e sorveterias, com nota, número de "
        "avaliações e faixa de preço por pessoa quando o Google informa. Aceita filtro de "
        "culinária (ex.: 'italiana', 'japonesa', 'comida mineira')."
    )
    GET_PLACE_DETAILS = (
        "Detalhes de um lugar: horários de cada dia da semana, faixa de preço, telefone, site, "
        "resumo, até 5 avaliações recentes, acessibilidade, estacionamento, formas de pagamento "
        "e comodidades. Aceita IDs do Google ou do OpenStreetMap (osm:...)."
    )
    CHECK_OPENING_HOURS = (
        "Verifica se um lugar estará aberto numa data e hora (horário local do lugar). Nos "
        "próximos 7 dias considera feriados e horários especiais informados ao Google. Diz "
        "quando fecha ou, se estiver fechado, quando abre. Use antes de fixar horários no roteiro."
    )
    FIND_NEARBY = (
        "Encontra lugares perto de um lugar já escolhido (place_id) ou de uma coordenada, ex.: "
        "restaurantes bem avaliados a até 500 m de um museu. Ordena por qualidade, distância "
        "ou popularidade."
    )
    SEARCH_ALONG_ROUTE = (
        "Busca paradas ao longo do trajeto entre origem e destino (ex.: 'posto de gasolina', "
        "'restaurante', 'mirante', 'café colonial'). Ideal para road trips. Requer Google Maps."
    )


class Params:
    LOCATION = "Cidade/região em texto, ex.: 'Curitiba, PR, Brasil'. Use isto OU coordinates."
    COORDINATES = "Centro da busca. Use isto OU location."
    RADIUS_KM = "Raio de busca em km (máx. 50)"
    RADIUS_M = "Raio de busca em metros"
    LIMIT = "Máximo de resultados (até 20)"
    CATEGORIES = "Categorias de lugar (até 5). Se omitido, usa 'query' como busca textual."
    QUERY = "Texto livre, ex.: 'café colonial', 'vinícola', 'Jardim Botânico'"
    FOOD_TYPES = "Tipos de estabelecimento (padrão: restaurant)"
    CUISINE = "Culinária ou estilo, ex.: 'italiana', 'japonesa', 'churrascaria', 'vegana'"
    PLACE_ID = "ID retornado pelas buscas (Google ou osm:<tipo>:<id>)"
    MIN_RATING = "Nota mínima de 1 a 5 (Google)"
    MIN_REVIEWS = "Mínimo de avaliações, para evitar lugares com poucas notas (Google)"
    OPEN_NOW = "Somente lugares abertos agora (Google)"
    PRICE_LEVELS = (
        "Níveis de preço aceitos (Google): free, inexpensive, moderate, expensive, very_expensive"
    )
    RANK_BY = (
        "Ordenação: relevance (nota ponderada pelo nº de avaliações), distance ou popularity "
        "(nº de avaliações)"
    )
    DATETIME_LOCAL = "Data e hora no horário local do lugar, ex.: '2026-12-12T10:30'"
    NEARBY_CATEGORIES = "Categorias procuradas ao redor (até 5)"
    NEARBY_PLACE_ID = "Lugar de referência (use isto OU coordinates)"
    NEARBY_COORDINATES = "Ponto de referência (use isto OU place_id)"
    ALONG_ROUTE_QUERY = "O que procurar no caminho, ex.: 'posto de gasolina', 'restaurante'"


class Fields:
    ID = "ID de origem: ID do Google Places ou osm:<tipo>:<id>"
    DISTANCE_KM = "Distância em linha reta do centro da busca"
    RATING = "Nota média de 1 a 5 (Google). OSM não fornece avaliações: null"
    USER_RATING_COUNT = "Número de avaliações no Google"
    PRICE_LEVEL = "Nível de preço relativo informado pelo Google"
    PRICE_RANGE = "Faixa de preço por pessoa informada pelo Google (valores reais, quando houver)"
    OPENING_HOURS = "Horários como informados pelo provedor"
    TAGS = "Tags brutas relevantes do OSM"
    REVIEWS = "Avaliações recentes do Google (texto resumido); cite o autor ao exibir"
    REVIEW_PUBLISHED = "Quando foi publicada (texto relativo do Google)"
    AMENITIES = "Comodidades informadas pelo Google (acessibilidade, estacionamento, pagamento…)"
    IS_OPEN = "true/false; null quando o provedor não informa horários"


class Notes:
    NO_PLACES = "Nenhum lugar encontrado; tente aumentar o raio, mudar as categorias ou os filtros."
    NO_RESTAURANTS = "Nenhum estabelecimento encontrado com esses filtros."
    NO_GOOGLE_KEY = (
        "Google Maps não configurado (GOOGLE_MAPS_API_KEY): usando OpenStreetMap, sem avaliações, "
        "preços nem horários estruturados."
    )
    GOOGLE_FAILED = "Google Maps falhou ({error}); usando OpenStreetMap como alternativa."
    OSM_HOURS_UNPARSED = (
        "O OpenStreetMap só fornece o horário em texto; não foi possível confirmar se estará "
        "aberto."
    )
    REGULAR_HOURS_ONLY = (
        "Data além dos próximos 7 dias: verificado o horário regular; feriados podem alterar."
    )
    NO_HOURS = "O Google não informa horários para este lugar."
    ALONG_ROUTE_SUMMARY = "Trajeto de referência: {km} km, cerca de {minutes} min."


class Errors:
    MISSING_SEARCH = "Informe 'categories' e/ou 'query'."
    MISSING_LOCATION = "Informe 'location' (texto) ou 'coordinates'."
    NO_VALID_CATEGORY = "Nenhuma categoria válida informada."
    OVERPASS_CIRCUIT_OPEN = "Overpass temporariamente indisponível (circuit breaker aberto)."
    OVERPASS_NOT_CONFIGURED = "Nenhuma instância Overpass configurada."
    INVALID_PLACE_ID = "place_id inválido. Formato esperado: osm:<node|way|relation>:<id>"
    INVALID_GOOGLE_PLACE_ID = "place_id do Google inválido."
    PLACE_NOT_FOUND = "Lugar não encontrado: {place_id}"
    PLACE_WITHOUT_NAME = "Lugar sem nome no provedor: {place_id}"
    PLACE_WITHOUT_LOCATION = "O lugar {place_id} não tem coordenadas no provedor."
    GOOGLE_REQUIRED = (
        "Esta operação requer Google Maps. Configure GOOGLE_MAPS_API_KEY no .env do projeto."
    )
    NEARBY_ONE_ORIGIN = "Informe exatamente um entre 'place_id' e 'coordinates'."
    ROUTE_WITHOUT_POLYLINE = "O Google não retornou o traçado da rota."


class Sources:
    GOOGLE = "google_maps"
    OSM = "openstreetmap"
    NOMINATIM_FALLBACK = "openstreetmap (nominatim fallback)"
