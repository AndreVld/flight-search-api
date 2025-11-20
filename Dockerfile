FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir poetry==1.8.3

RUN poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-dev --no-interaction --no-ansi

COPY src/ ./src/
COPY chunk.json ./
COPY av_parser/ ./av_parser/

# Добавляем src в PYTHONPATH для импорта модулей
ENV PYTHONPATH=/app/src:${PYTHONPATH}

ENV FLY_SEARCH_HOST=0.0.0.0
ENV FLY_SEARCH_PORT=8000
ENV FLY_SEARCH_RELOAD=false
ENV FLY_SEARCH_LOG_LEVEL=INFO
ENV FLY_SEARCH_WORKERS=4

EXPOSE 8000

CMD gunicorn fly_search.app:app \
    --bind ${FLY_SEARCH_HOST}:${FLY_SEARCH_PORT} \
    --workers ${FLY_SEARCH_WORKERS} \
    --worker-class uvicorn.workers.UvicornWorker \
    --access-logfile - \
    --error-logfile - \
    --log-level info

