FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install ".[postgres]"

COPY config ./config

EXPOSE 8000
# Os MCP Servers são iniciados pela própria API como processos filhos (stdio).
CMD ["uvicorn", "meu_passeio.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
