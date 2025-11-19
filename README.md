# Fly Search API

FastAPI сервис для поиска и нормализации данных о перелётах от провайдера Avia API.

## Описание

Сервис получает данные о поиске перелётов через методы `avia_api.start_search` и `get_chunk`, конвертирует их во внутренний формат и возвращает в виде `ServiceResponse`.

## Важно: файл данных `chunk.json`

**⚠️ Важное замечание о структуре данных:**

Класс `AviaApi` из `av_parser/api_service.py` ожидает файл `chunk.json`.

В папке `av_parser/` находится файл `chunks.json`, но `AviaApi` ищет именно `chunk.json`.

### API Endpoints

- `GET /health` - проверка работоспособности сервиса
- `GET /get_flights?pid=<optional_pid>` - получение результатов поиска перелётов

### Пример запроса

```bash
curl "http://localhost:8000/get_flights?pid=test-123"
```


## Тестирование

```bash
# Запуск всех тестов
poetry run pytest

# С подробным выводом
poetry run pytest -v

```

## Линтинг и форматирование

```bash
# Проверка кода
poetry run ruff check .

# Автоматическое исправление
poetry run ruff check . --fix
```

## Структура проекта

```
fly_search/
├── av_parser/              # Исходные файлы тестового задания (не изменяются)
│   ├── api_service.py      # AviaApi класс (не изменяется)
│   ├── chunks.json         # Исходные данные (не используется напрямую)
│   ├── models.py           # Pydantic модели для ServiceResponse
│   └── readme.md           # Описание задания
├── src/
│   └── fly_search/
│       ├── api/            # FastAPI роуты и зависимости
│       │   ├── routes.py   # Эндпоинт /get_flights
│       │   └── dependencies.py
│       ├── domain/          # Доменная логика
│       │   ├── ports/       # Интерфейсы (AviaApiProtocol)
│       │   └── services/    # Бизнес-логика (конвертация, поиск)
│       ├── app.py           # FastAPI приложение
│       ├── config.py        # Конфигурация (Pydantic Settings)
│       ├── logging_config.py # Настройка логирования
│       └── __main__.py      # Точка входа
├── tests/                   # Тесты
│   ├── api/                 # Интеграционные тесты API
│   ├── domain/              # Юнит-тесты доменной логики
│   └── conftest.py          # Pytest фикстуры
├── chunk.json               # Файл данных для AviaApi (см. раздел выше)
├── pyproject.toml          # Конфигурация Poetry и зависимостей
└── README.md
```

## Архитектура

- **Domain Layer** (`src/fly_search/domain/`): Бизнес-логика

  - `ports/`: Интерфейсы (протоколы) для внешних зависимостей
  - `services/`: Доменные сервисы (конвертация, поиск)

- **Application Layer** (`src/fly_search/api/`): FastAPI роуты и dependency injection

- **Infrastructure**: Логирование, конфигурация

## Логирование

используется стандартный модуль `logging` Python. Все логи включают:

- `pid` (process identifier) - идентификатор процесса/запроса
- Структурированное логирование с контекстом

Логи выводятся в консоль в формате:

```
[timestamp] [level] [pid] message
```
