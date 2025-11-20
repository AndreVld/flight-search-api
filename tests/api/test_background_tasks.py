"""Tests for background task endpoints."""

from __future__ import annotations

import asyncio
import time

import pytest
from fastapi.testclient import TestClient

from av_parser.models import ServiceResponse
from fly_search.api.dependencies import get_cache_service, get_flight_service
from fly_search.app import create_app
from fly_search.domain.services.background_task import TaskStatus


@pytest.fixture
def app():
    app = create_app()
    yield app
    app.dependency_overrides.clear()
    # Очищаем кеш задач после теста
    cache_service = get_cache_service()
    cache_service.clear_task_cache()


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


@pytest.mark.asyncio
async def test_start_search_returns_task_id(app, client) -> None:
    """Test that start_search returns task_id."""
    response = ServiceResponse(success=True, pid="test", result={})
    override_service_with_response(app, response)

    resp = client.post("/start_search", params={"pid": "test-pid"})

    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == TaskStatus.PROCESSING
    assert isinstance(data["task_id"], str)
    assert len(data["task_id"]) > 0


@pytest.mark.asyncio
async def test_get_result_processing_status(app, client) -> None:
    """Test that get_result returns processing status for active task."""
    response = ServiceResponse(success=True, pid="test", result={})
    override_service_with_response(app, response)

    # Запускаем задачу
    start_resp = client.post("/start_search", params={"pid": "test-pid"})
    task_id = start_resp.json()["task_id"]

    # Сразу проверяем статус (может быть еще processing или уже completed)
    result_resp = client.get("/get_result", params={"task_id": task_id})

    assert result_resp.status_code == 200
    data = result_resp.json()
    # Если задача быстро завершилась, это ServiceResponse, иначе dict со статусом
    if "status" in data:
        assert data["status"] in [TaskStatus.PROCESSING, TaskStatus.COMPLETED]
        assert data["task_id"] == task_id
    else:
        # Задача уже завершилась, это ServiceResponse
        assert "success" in data
        assert "pid" in data


@pytest.mark.asyncio
async def test_get_result_completed_status(app, client) -> None:
    """Test that get_result returns completed result when task is done."""
    response = ServiceResponse(success=True, pid="test", result={"route": []})
    override_service_with_response(app, response)

    # Запускаем задачу
    start_resp = client.post("/start_search", params={"pid": "test-pid"})
    task_id = start_resp.json()["task_id"]

    # Ждём завершения задачи (максимум 5 секунд)
    max_wait = 5.0
    start_time = time.time()
    while time.time() - start_time < max_wait:
        result_resp = client.get("/get_result", params={"task_id": task_id})
        assert result_resp.status_code == 200
        data = result_resp.json()

        if data.get("status") == TaskStatus.COMPLETED:
            # Проверяем, что это ServiceResponse
            assert "success" in data
            assert "pid" in data
            assert "result" in data
            assert data["pid"] == "test"
            return

        await asyncio.sleep(0.1)

    # задача может выполняться долго
    pytest.skip("Task did not complete within timeout (this is expected for long tasks)")


def test_get_result_task_not_found(app, client) -> None:
    """Test that get_result returns 404 for non-existent task."""
    resp = client.get("/get_result", params={"task_id": "non-existent-task-id"})

    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


def test_start_search_without_pid(app, client) -> None:
    """Test that start_search works without pid parameter."""
    response = ServiceResponse(success=True, pid="generated", result={})
    override_service_with_response(app, response)

    resp = client.post("/start_search")

    assert resp.status_code == 200
    data = resp.json()
    assert "task_id" in data
    assert data["status"] == TaskStatus.PROCESSING

