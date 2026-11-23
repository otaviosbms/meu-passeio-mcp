"""Textos dos schemas de domínio compartilhados."""


class Fields:
    START_TIME = "HH:MM, horário sugerido"
    WAYPOINT_ADDRESS = "Endereço ou nome do lugar, ex.: 'Parque Barigui, Curitiba'"
    WAYPOINT_PLACE_ID = "ID do Google Places retornado pelas buscas de lugares"


class Errors:
    WAYPOINT_EXACTLY_ONE = "Informe exatamente um entre coordinates, address e place_id."
