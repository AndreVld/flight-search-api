"""Integration tests for the /get_flights endpoint."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from av_parser.models import ServiceResponse
from fly_search.api.dependencies import get_flight_service
from fly_search.app import create_app


@pytest.fixture
def app():
    app = create_app()
    yield app
    app.dependency_overrides.clear()



@pytest.fixture
def client(app) -> TestClient:
    return TestClient(app)


def override_service(app, response: ServiceResponse) -> None:
    class _Service:
        async def get_offers(self, pid: str | None = None) -> ServiceResponse:
            return ServiceResponse(
                success=response.success,
                pid=pid or response.pid,
                result=response.result,
            )

    app.dependency_overrides[get_flight_service] = lambda: _Service()


def test_get_flights_success(app, client) -> None:
    response = ServiceResponse(success=True, pid="pid", result={"route": []})
    override_service(app, response)

    resp = client.get("/get_flights", params={"pid": "external"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["pid"] == "external"
    assert data["result"] == {"route": []}


def test_get_flights_failure(app, client) -> None:
    response = ServiceResponse(success=False, pid="pid", result={})
    override_service(app, response)

    resp = client.get("/get_flights")

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is False
    assert data["pid"] == "pid"
