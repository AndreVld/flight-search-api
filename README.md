# Fly Search API

## Описание

Сервис получает данные о поиске перелётов через методы `avia_api.start_search` и `get_chunk`, конвертирует их во внутренний формат и возвращает в виде `ServiceResponse`.

## Важно: файл данных `chunk.json`

**⚠️ Важное замечание о структуре данных:**

Класс `AviaApi` из `av_parser/api_service.py` ожидает файл `chunk.json`.

В папке `av_parser/` находится файл `chunks.json`, но `AviaApi` ищет именно `chunk.json`.

### API Endpoints

- `GET /health` - проверка работоспособности сервиса
- `GET /get_flights?pid=<optional_pid>` - получение результатов поиска перелётов (с кешированием на 3 минуты)
- `POST /start_search?pid=<optional_pid>` - запуск фоновой задачи поиска
- `GET /get_result?task_id=<task_id>` - получение результата фоновой задачи
- `GET /docs` - интерактивная документация API (Swagger UI)


### Примеры использования

#### Получение результатов поиска (синхронно)

```bash
# С указанием pid
curl "http://localhost:8000/get_flights?pid=test-123"

# Без pid (будет сгенерирован автоматически)
curl "http://localhost:8000/get_flights"
```

#### Запуск фоновой задачи

```bash
# Запуск задачи
curl -X POST "http://localhost:8000/start_search?pid=test-123"

# Ответ: {"task_id": "uuid-here", "status": "processing"}

# Получение результата
curl "http://localhost:8000/get_result?task_id=uuid-here"

# Пока задача выполняется, вернется:
# {"task_id": "uuid-here", "status": "processing", "pid": "test-123"}

# После завершения вернется ServiceResponse с результатами
```


## Установка и запуск

### Локальная разработка

```bash
# Установка зависимостей
poetry install

# Запуск сервера разработки
poetry run dev-server
```

### Docker Compose

```bash
# Сборка и запуск контейнера
docker compose up --build

# Запуск в фоновом режиме
docker compose up -d

# Просмотр логов
docker compose logs -f

# Остановка
docker compose down
```

### Переменные окружения

Все настройки можно переопределить через переменные окружения с префиксом `FLY_SEARCH_`:

#### Сервер

- `FLY_SEARCH_HOST` - хост сервера (по умолчанию: `0.0.0.0`)
- `FLY_SEARCH_PORT` - порт сервера (по умолчанию: `8000`)
- `FLY_SEARCH_RELOAD` - включить auto-reload в разработке (по умолчанию: `true`)
- `FLY_SEARCH_WORKERS` - количество Gunicorn workers (по умолчанию: `4`, только для Docker)

#### Кеширование

- `FLY_SEARCH_CACHE_RESPONSE_TTL` - TTL кеша ответов в секундах (по умолчанию: `180` - 3 минуты)
- `FLY_SEARCH_CACHE_RESPONSE_SIZE` - максимальное количество кешированных ответов (по умолчанию: `100`)
- `FLY_SEARCH_CACHE_TASK_TTL` - TTL кеша задач в секундах (по умолчанию: `3600` - 1 час)
- `FLY_SEARCH_CACHE_TASK_SIZE` - максимальное количество кешированных задач (по умолчанию: `1000`)

#### Потоки и производительность

- `FLY_SEARCH_MAX_CONCURRENT_THREADS` - максимальное количество одновременных потоков для обработки блокирующих операций (по умолчанию: `10`)
- `FLY_SEARCH_CHUNK_QUEUE_TIMEOUT` - таймаут для получения чанка из очереди в секундах (по умолчанию: `0.1`)
- `FLY_SEARCH_THREAD_JOIN_TIMEOUT` - таймаут для завершения потока в секундах (по умолчанию: `1.0`)

#### Логирование

- `FLY_SEARCH_LOG_LEVEL` - уровень логирования: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (по умолчанию: `INFO`)

**Примечание**: 
- В Docker используется Gunicorn с Uvicorn workers для production-ready развертывания
- Переменные можно задать через `.env` файл или напрямую в `docker-compose.yml`

## Тестирование

```bash

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
├── av_parser/                    # Исходные файлы тестового задания (не изменяются)
│   ├── api_service.py            # AviaApi класс (не изменяется)
│   ├── chunks.json               # Исходные данные (не используется напрямую)
│   ├── models.py                 # Pydantic модели для ServiceResponse
│   └── readme.md                 # Описание задания
├── src/
│   └── fly_search/
│       ├── api/                  # FastAPI роуты и зависимости
│       │   ├── routes.py         # API endpoints (/get_flights, /start_search, /get_result)
│       │   └── dependencies.py   # Dependency injection для FastAPI
│       ├── domain/               # Доменная логика (Clean Architecture)
│       │   ├── ports/            # Интерфейсы (AviaApiProtocol)
│       │   └── services/          # Бизнес-логика
│       │       ├── converter.py  # Конвертация данных провайдера
│       │       ├── flight_search.py  # Сервис поиска перелётов
│       │       └── background_task.py  # Сервис фоновых задач
│       ├── infrastructure/       # Инфраструктурный слой
│       │   ├── avia_api_adapter.py  # Адаптер для AviaApi (неблокирующая работа)
│       │   ├── cache_service.py     # Сервис кеширования (TTL-based)
│       │   └── background_task_manager.py  # Менеджер фоновых задач
│       ├── app.py                # FastAPI приложение
│       ├── config.py             # Конфигурация (Pydantic Settings)
│       ├── logging_config.py     # Настройка логирования
│       └── __main__.py           # Точка входа
├── tests/                        # Тесты
│   ├── api/                      # Интеграционные тесты API
│   ├── domain/                   # Юнит-тесты доменной логики
│   ├── infrastructure/           # Тесты инфраструктурного слоя
│   └── conftest.py               # Pytest фикстуры
├── chunk.json                    # Файл данных для AviaApi (см. раздел выше)
├── pyproject.toml                # Конфигурация Poetry и зависимостей
├── Dockerfile                    # Docker образ приложения
├── docker-compose.yml            # Docker Compose конфигурация
├── .dockerignore                 # Исключения для Docker сборки
└── README.md
```

## Архитектура


### Слои архитектуры

- **Domain Layer** (`src/fly_search/domain/`): Бизнес-логика, не зависящая от внешних библиотек
  - `ports/`: Интерфейсы (протоколы) для внешних зависимостей (`AviaApiProtocol`)
  - `services/`: Доменные сервисы
    - `converter.py`: Конвертация данных провайдера в внутренний формат
    - `flight_search.py`: Оркестрация процесса поиска
    - `background_task.py`: Управление фоновыми задачами

- **Application Layer** (`src/fly_search/api/`): FastAPI роуты и dependency injection
  - `routes.py`: HTTP endpoints
  - `dependencies.py`: Wiring зависимостей через FastAPI Depends

- **Infrastructure Layer** (`src/fly_search/infrastructure/`): Реализация портов и внешних зависимостей
  - `avia_api_adapter.py`: Адаптер для AviaApi с неблокирующей обработкой блокирующих операций
  - `cache_service.py`: TTL-based кеширование ответов и задач
  - `background_task_manager.py`: Менеджер фоновых задач с кешированием результатов

### Ключевые особенности

- **Неблокирующая работа**: Блокирующие операции `AviaApi` выполняются в отдельных потоках
- **Кеширование**: TTL-based кеш для ответов (3 минуты) и задач (1 час)
- **Фоновые задачи**: Асинхронная обработка длительных операций поиска
- **Dependency Injection**: Все зависимости инжектируются через FastAPI Depends
- **Типизация**: Полная типизация с использованием type hints

## Логирование

Используется стандартный модуль `logging` Python. Все логи включают:

- `pid` (process identifier) - идентификатор процесса/запроса
- Структурированное логирование с контекстом
- События (`event`) для отслеживания операций (cache_hit, call, start_task, etc.)

Логи выводятся в консоль в формате:

```
[timestamp] [level] [pid] message
```

Примеры событий:
- `cache_hit` - попадание в кеш
- `call` - вызов endpoint
- `start_task` - запуск фоновой задачи
- `task_started` - задача успешно запущена
- `get_result` - запрос результата задачи

## Кеширование

Сервис использует TTL-based кеширование для оптимизации производительности:

- **Кеш ответов** (`/get_flights`): 
  - TTL: 3 минуты (180 секунд)
  - Ключ кеша формируется на основе `pid` параметра
  - Максимальный размер: 100 записей

- **Кеш задач** (фоновые задачи):
  - TTL: 1 час (3600 секунд)
  - Хранит статус и результаты фоновых задач
  - Максимальный размер: 1000 записей

## Фоновые задачи

Сервис поддерживает асинхронную обработку длительных операций поиска:

1. **Запуск задачи**: `POST /start_search` возвращает `task_id`
2. **Проверка статуса**: `GET /get_result?task_id=...` возвращает:
   - `{"status": "processing"}` - задача выполняется
   - `ServiceResponse` - задача завершена успешно
   - `HTTP 500` - задача завершилась с ошибкой

Задачи выполняются в фоне через `asyncio.create_task` и результаты кешируются.

## Технические детали

### Неблокирующая работа с AviaApi

`AviaApi` содержит блокирующий `time.sleep(15)` в методе `get_chunk()`. Для обеспечения неблокирующей работы FastAPI приложения:

- Блокирующие операции выполняются в отдельных потоках
- Используется `threading.Thread` с собственным event loop
- Коммуникация между потоками через `queue.Queue`
- Ограничение количества одновременных потоков через семафор

Это позволяет FastAPI оставаться отзывчивым даже при выполнении длительных операций.
