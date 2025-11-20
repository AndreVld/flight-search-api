"""Tests for CacheService."""

from __future__ import annotations

import time

from av_parser.models import ServiceResponse
from fly_search.infrastructure.cache_service import CacheService


def test_cache_service_stores_and_retrieves_response() -> None:
    """Test that cache service can store and retrieve responses."""
    cache = CacheService(response_cache_ttl=60, response_cache_size=10)
    test_key = "test_key"
    test_value = ServiceResponse(success=True, pid="test", result={})

    # Кеш пуст
    assert cache.get_response(test_key) is None

    # Сохраняем значение
    cache.set_response(test_key, test_value)

    # Получаем из кеша
    cached = cache.get_response(test_key)
    assert cached is not None
    assert cached.success == test_value.success
    assert cached.pid == test_value.pid


def test_cache_service_ttl_expiration() -> None:
    """Test that cache entries expire after TTL."""
    cache = CacheService(response_cache_ttl=1, response_cache_size=10)  # 1 секунда
    test_key = "test_key"
    test_value = ServiceResponse(success=True, pid="test", result={})

    # Сохраняем значение
    cache.set_response(test_key, test_value)

    # Сразу получаем - должно быть в кеше
    assert cache.get_response(test_key) is not None

    # Ждём истечения TTL
    time.sleep(1.1)

    # После истечения TTL - должно быть None
    assert cache.get_response(test_key) is None


def test_cache_service_build_cache_key() -> None:
    """Test cache key building."""
    key1 = CacheService.build_cache_key("flights", pid="test-123")
    key2 = CacheService.build_cache_key("flights", pid="test-123")
    key3 = CacheService.build_cache_key("flights", pid="test-456")

    # Одинаковые параметры дают одинаковый ключ
    assert key1 == key2

    # Разные параметры дают разные ключи
    assert key1 != key3

    # Ключ начинается с префикса
    assert key1.startswith("flights:")


def test_cache_service_task_storage() -> None:
    """Test that cache service can store and retrieve tasks."""
    cache = CacheService(task_cache_ttl=60, task_cache_size=10)
    task_id = "task-123"
    task_data = {"status": "completed", "result": {"success": True}}

    # Кеш пуст
    assert cache.get_task(task_id) is None

    # Сохраняем задачу
    cache.set_task(task_id, task_data)

    # Получаем из кеша
    cached = cache.get_task(task_id)
    assert cached is not None
    assert cached["status"] == "completed"
    assert cached["result"]["success"] is True


def test_cache_service_clear_methods() -> None:
    """Test cache clearing methods."""
    cache = CacheService(response_cache_ttl=60, response_cache_size=10)

    # Добавляем значения
    cache.set_response("key1", "value1")
    cache.set_response("key2", "value2")

    # Проверяем, что они есть
    assert cache.get_response("key1") is not None
    assert cache.get_response("key2") is not None

    # Очищаем кеш
    cache.clear_response_cache()

    # После очистки должно быть пусто
    assert cache.get_response("key1") is None
    assert cache.get_response("key2") is None

