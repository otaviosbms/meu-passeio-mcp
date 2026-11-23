"""Textos das tools de roteiros salvos."""


class Tools:
    SAVE_TRIP = (
        "Salva um roteiro pronto (TripPlan: destino, datas, dias com atividades, custos, "
        "observações e fontes) no banco do Meu Passeio e devolve o ID. Use depois que o usuário "
        "aprovar o roteiro, para poder reabri-lo ou ajustá-lo depois."
    )
    LIST_TRIPS = "Lista os roteiros salvos, do mais recente para o mais antigo (ID e título)."
    GET_TRIP = "Abre um roteiro salvo pelo ID, com o plano completo."
    UPDATE_TRIP = (
        "Substitui o plano de um roteiro salvo. Envie o plano completo já ajustado (use get_trip "
        "antes para partir da versão salva)."
    )


class Params:
    PLAN = (
        "Roteiro completo. Em cada atividade, mantenha place_id, location e source vindos das "
        "tools; em cost_estimates, explique nas notes a fonte de cada valor."
    )
    PLAN_UPDATE = "Plano completo, já com as alterações"
    TITLE = "Título do roteiro; se omitido, usa plan.title"
    TRIP_ID = "ID do roteiro (ex.: trip_1a2b3c4d5e6f)"
    LIMIT = "Máximo de roteiros na lista"


class Messages:
    SAVED = "Roteiro salvo com o ID {trip_id}."
    UPDATED = "Roteiro {trip_id} atualizado."


class Errors:
    NOT_FOUND = "Roteiro não encontrado: {trip_id}"
