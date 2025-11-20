"""Tests for caching in get_flights endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from av_parser.models import ServiceResponse
from fly_search.api.dependencies import get_cache_service, get_flight_service
from fly_search.app import create_app


@pytest.fixture
def app():
    app = create_app()
    yield app
    app.dependency_overrides.clear()
    # Очищаем кеш после теста
    cache = get_cache_service()
    cache.clear_response_cache()


@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def override_service_with_response(app, response: ServiceResponse) -> None:
    """Override service to return specific response."""

    class _Service:
        async def get_offers(self, pid: str | None = None) -> ServiceResponse:
            return ServiceResponse(
                success=response.success,
                pid=pid or response.pid,
                result=response.result,
            )

    app.dependency_overrides[get_flight_service] = lambda: _Service()


def test_get_flights_caches_response(app, client) -> None:
    """Test that get_flights caches responses."""
    response = ServiceResponse(success=True, pid="test-pid", result={"route": []})
    override_service_with_response(app, response)

    # Первый запрос - не из кеша
    resp1 = client.get("/get_flights", params={"pid": "test-pid"})
    assert resp1.status_code == 200
    data1 = resp1.json()

    # Второй запрос с тем же pid - должен быть из кеша
    resp2 = client.get("/get_flights", params={"pid": "test-pid"})
    assert resp2.status_code == 200
    data2 = resp2.json()

    # Результаты должны быть одинаковыми
    assert data1 == data2
    assert data1["pid"] == "test-pid"


def test_get_flights_different_pid_different_cache(app, client) -> None:
    """Test that different pid values use different cache keys."""
    response1 = ServiceResponse(success=True, pid="pid1", result={"route1": []})
    response2 = ServiceResponse(success=True, pid="pid2", result={"route2": []})

    # Мокаем сервис, чтобы возвращать разные результаты для разных pid
    call_count = {"count": 0}

    class _Service:
        async def get_offers(self, pid: str | None = None) -> ServiceResponse:
            call_count["count"] += 1
            if pid == "pid1":
                return response1
            return response2

    app.dependency_overrides[get_flight_service] = lambda: _Service()

    # Первый запрос с pid1
    resp1 = client.get("/get_flights", params={"pid": "pid1"})
    assert resp1.status_code == 200
    assert call_count["count"] == 1

    # Второй запрос с pid1 - из кеша
    resp2 = client.get("/get_flights", params={"pid": "pid1"})
    assert resp2.status_code == 200
    assert call_count["count"] == 1  # Не увеличился

    # Запрос с pid2 - новый запрос
    resp3 = client.get("/get_flights", params={"pid": "pid2"})
    assert resp3.status_code == 200
    assert call_count["count"] == 2  # Увеличился

    # Проверяем, что результаты разные
    assert resp1.json()["pid"] == "pid1"
    assert resp3.json()["pid"] == "pid2"


def test_get_flights_cache_without_pid(app, client) -> None:
    """Test that get_flights caches responses even without pid."""
    response = ServiceResponse(success=True, pid="generated", result={})
    override_service_with_response(app, response)

    # Первый запрос без pid
    resp1 = client.get("/get_flights")
    assert resp1.status_code == 200

    # Второй запрос без pid - должен быть из кеша
    resp2 = client.get("/get_flights")
    assert resp2.status_code == 200

    # Результаты должны быть одинаковыми
    assert resp1.json() == resp2.json()
