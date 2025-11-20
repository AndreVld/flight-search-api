"""Cache service for storing API responses and background task results."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

from cachetools import TTLCache

from ..config import get_settings

T = TypeVar("T")


class CacheService:
    """
    Service for managing TTL-based caches.

    Provides separate caches for API responses and background tasks
    with configurable TTL and size limits.
    """

    def __init__(
        self,
        response_cache_ttl: int | None = None,
        response_cache_size: int | None = None,
        task_cache_ttl: int | None = None,
        task_cache_size: int | None = None,
    ) -> None:
        """
        Initialize cache service with configurable TTL and size.

        Args:
            response_cache_ttl: TTL for response cache in seconds (default from config)
            response_cache_size: Max size for response cache (default 100)
            task_cache_ttl: TTL for task cache in seconds (default from config)
            task_cache_size: Max size for task cache (default 1000)
        """
        settings = get_settings()

        # Response cache (for get_flights results) - 3 minutes default
        # In-memory cache, works within single process
        self._response_cache = TTLCache(
            maxsize=response_cache_size or settings.cache_response_size,
            ttl=response_cache_ttl or settings.cache_response_ttl,
        )

        # Task cache (for background tasks) - 1 hour default
        # In-memory cache for single process
        self._task_cache = TTLCache(
            maxsize=task_cache_size or settings.cache_task_size,
            ttl=task_cache_ttl or settings.cache_task_ttl,
        )

        # File-based cache for tasks to share between Gunicorn workers
        # Используем файловый кеш для задач, чтобы они были доступны между процессами
        self._task_cache_dir = Path(
            os.environ.get("FLY_SEARCH_TASK_CACHE_DIR", tempfile.gettempdir())
        ) / "fly_search_tasks"
        self._task_cache_dir.mkdir(parents=True, exist_ok=True)
        self._task_cache_ttl = task_cache_ttl or settings.cache_task_ttl

        # Очищаем старые файлы при инициализации
        self._cleanup_old_task_files()

    def get_response(self, key: str) -> Any | None:
        """
        Get cached response by key.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        return self._response_cache.get(key)

    def set_response(self, key: str, value: Any) -> None:
        """
        Store response in cache.

        Args:
            key: Cache key
            value: Value to cache
        """
        self._response_cache[key] = value

    def _cleanup_old_task_files(self) -> None:
        """Remove expired task cache files."""
        current_time = time.time()
        for task_file in self._task_cache_dir.glob("*.json"):
            try:
                with open(task_file, encoding="utf-8") as f:
                    data = json.load(f)
                    if current_time - data.get("timestamp", 0) > self._task_cache_ttl:
                        task_file.unlink(missing_ok=True)
            except (json.JSONDecodeError, OSError, KeyError):
                task_file.unlink(missing_ok=True)

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get cached task result by task_id.

        Проверяет сначала in-memory кеш, затем файловый кеш для работы между процессами.

        Args:
            task_id: Task identifier

        Returns:
            Task data dict or None if not found/expired
        """
        # Сначала проверяем in-memory кеш
        cached = self._task_cache.get(task_id)
        if cached is not None:
            return cached

        # Проверяем файловый кеш (для работы между Gunicorn workers)
        task_file = self._task_cache_dir / f"{task_id}.json"
        if not task_file.exists():
            return None

        try:
            with open(task_file, encoding="utf-8") as f:
                data = json.load(f)
                # Проверяем TTL
                if time.time() - data.get("timestamp", 0) > self._task_cache_ttl:
                    task_file.unlink(missing_ok=True)
                    return None
                # Восстанавливаем task_data из JSON
                task_data = data.get("data")
                if not task_data:
                    return None

                # Восстанавливаем ServiceResponse из dict если нужно
                # Проверяем, что result - это dict с полями ServiceResponse
                if (
                    "result" in task_data
                    and isinstance(task_data["result"], dict)
                    and "success" in task_data["result"]
                    and "pid" in task_data["result"]
                    and "result" in task_data["result"]
                ):
                    from av_parser.models import ServiceResponse

                    try:
                        # Восстанавливаем ServiceResponse из dict
                        task_data["result"] = ServiceResponse.model_validate(
                            task_data["result"]
                        )
                    except Exception:
                        # Если не получилось, оставляем как dict
                        pass

                # Сохраняем в in-memory кеш для быстрого доступа
                self._task_cache[task_id] = task_data
                return task_data
        except (json.JSONDecodeError, OSError, KeyError):
            task_file.unlink(missing_ok=True)
            return None

    def set_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """
        Store task result in cache.

        Сохраняет в in-memory и файловый кеш для работы между процессами.

        Args:
            task_id: Task identifier
            task_data: Task data to cache (может содержать ServiceResponse)
        """
        # Сохраняем в in-memory кеш
        self._task_cache[task_id] = task_data

        # Сериализуем task_data для файлового кеша
        # Если в task_data есть ServiceResponse, конвертируем в dict
        serializable_data = task_data.copy()
        if "result" in serializable_data:
            result = serializable_data["result"]
            if hasattr(result, "model_dump"):
                # Если result - это Pydantic модель (ServiceResponse), сериализуем её
                serializable_data["result"] = result.model_dump()
            elif isinstance(result, dict):
                # Если result уже dict, оставляем как есть
                pass

        # Сохраняем в файловый кеш для работы между Gunicorn workers
        task_file = self._task_cache_dir / f"{task_id}.json"
        try:
            with open(task_file, "w", encoding="utf-8") as f:
                json.dump(
                    {"timestamp": time.time(), "data": serializable_data},
                    f,
                    ensure_ascii=False,
                )
        except OSError as e:
            # Логируем ошибки записи файла, но не прерываем выполнение
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                "Failed to write task cache file",
                extra={"task_id": task_id, "error": str(e), "path": str(task_file)},
            )

    @staticmethod
    def build_cache_key(prefix: str, *args: Any, **kwargs: Any) -> str:
        """
        Build cache key from prefix and parameters.

        Args:
            prefix: Key prefix (e.g., 'flights')
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key

        Returns:
            Cache key string
        """
        # Создаём строковое представление аргументов для хеширования
        key_parts = [prefix]
        if args:
            key_parts.append(str(args))
        if kwargs:
            # Сортируем kwargs для консистентности
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(str(sorted_kwargs))

        key_string = ":".join(key_parts)
        # Хешируем для компактности и безопасности
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"{prefix}:{key_hash}"

    def clear_response_cache(self) -> None:
        """Clear all entries from response cache."""
        self._response_cache.clear()

    def clear_task_cache(self) -> None:
        """Clear all entries from task cache."""
        self._task_cache.clear()


def cached_response(
    cache_service: CacheService,
    key_prefix: str = "flights",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for caching async function results.

    Args:
        cache_service: CacheService instance
        key_prefix: Prefix for cache keys

    Returns:
        Decorator function
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Строим ключ кеша из аргументов функции
            cache_key = CacheService.build_cache_key(key_prefix, *args, **kwargs)

            # Пытаемся получить из кеша
            cached_result = cache_service.get_response(cache_key)
            if cached_result is not None:
                return cached_result

            # Выполняем функцию и кешируем результат
            result = await func(*args, **kwargs)
            cache_service.set_response(cache_key, result)

            return result

        return wrapper

    return decorator

