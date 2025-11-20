"""Cache service for storing API responses and background task results."""

from __future__ import annotations

import hashlib
from collections.abc import Callable
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
        self._response_cache = TTLCache(
            maxsize=response_cache_size or settings.cache_response_size,
            ttl=response_cache_ttl or settings.cache_response_ttl,
        )

        # Task cache (for background tasks) - 1 hour default
        self._task_cache = TTLCache(
            maxsize=task_cache_size or settings.cache_task_size,
            ttl=task_cache_ttl or settings.cache_task_ttl,
        )

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

    def get_task(self, task_id: str) -> dict[str, Any] | None:
        """
        Get cached task result by task_id.

        Args:
            task_id: Task identifier

        Returns:
            Task data dict or None if not found/expired
        """
        return self._task_cache.get(task_id)

    def set_task(self, task_id: str, task_data: dict[str, Any]) -> None:
        """
        Store task result in cache.

        Args:
            task_id: Task identifier
            task_data: Task data to cache
        """
        self._task_cache[task_id] = task_data

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

