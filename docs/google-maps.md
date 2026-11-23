# Chave do Google Maps

[← Voltar ao README](../README.md)

Lugares e rotas usam a **Places API (New)** e a **Routes API** do Google Maps Platform. Sem a
chave, o server usa OpenStreetMap/OSRM, mas perde notas, preços, horários, trânsito e pedágios,
e as tools `search_along_route`, `estimate_toll_costs`, `estimate_meal_cost` e
`suggest_day_trip_destinations` ficam indisponíveis.

## Como obter

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/) e crie um projeto.
2. Em **Faturamento**, vincule uma conta de faturamento (o Google exige cartão, mesmo dentro da
   cota gratuita).
3. Em **APIs e serviços → Biblioteca**, ative **Places API (New)** (não a "Places API" antiga) e
   **Routes API**.
4. Em **APIs e serviços → Credenciais**, crie uma **Chave de API**.
5. Restrinja a chave: em **Restrições de API**, permita só **Places API (New)** e **Routes API**.
6. No `.env` da raiz do projeto, preencha `GOOGLE_MAPS_API_KEY=sua-chave`.
7. Reinicie o Claude Desktop.

O `.env` está no `.gitignore` e é lido pelo caminho absoluto do projeto, então funciona mesmo
quando o server é iniciado pelo Claude Desktop. A chave vai no header `X-Goog-Api-Key` e nunca
aparece em URLs, logs ou respostas.

## Custos

O Google Maps Platform cobra por chamada, com uma cota gratuita mensal por tipo de chamada. As
tools pedem só os campos necessários (`X-Goog-FieldMask`), mas nota, preço e horários estão nos
níveis mais caros da Places API.

- Confira a [tabela de preços](https://mapsplatform.google.com/pricing/).
- Crie um alerta em **Faturamento → Orçamentos e alertas**.
- Para limitar de fato o uso, reduza as **Cotas** diárias de cada API.
