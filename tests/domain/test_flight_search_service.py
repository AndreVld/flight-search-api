"""Tests for FlightSearchService."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import pytest

from fly_search.domain.services.converter import FlightOfferConverter
from fly_search.domain.services.flight_search import FlightSearchService


@dataclass
class FakeAviaApi:
    """Simple fake to simulate Avia API answers."""

    start_payload: dict[str, Any]
    chunks: list[dict[str, Any]]

    async def start_search(self) -> dict[str, Any]:
        await asyncio.sleep(0)
        return self.start_payload

    async def get_chunk(self, task_id: str) -> AsyncIterator[dict[str, Any]]:
        for chunk in self.chunks:
            await asyncio.sleep(0)
            yield chunk


@pytest.mark.asyncio
async def test_service_returns_success(chunk_builder) -> None:
    api = FakeAviaApi(
        start_payload={"success": True, "task_id": "task"},
        chunks=[chunk_builder()],
    )
    service = FlightSearchService(api, converter=FlightOfferConverter())

    response = await service.get_offers(pid="test")

    assert response.success is True
    assert response.pid == "test"
    assert "MOWLED20251217" in response.result


@pytest.mark.asyncio
async def test_empty_chunk_returns_empty_response(chunk_builder) -> None:
    api = FakeAviaApi(
        start_payload={"success": True, "task_id": "task"},
        chunks=[{}],
    )
    service = FlightSearchService(api)

    response = await service.get_offers(pid="test")

    assert response.success is False
    assert response.result == {}
    assert response.pid == "test"


@pytest.mark.asyncio
async def test_missing_task_id_returns_failure(chunk_builder, caplog) -> None:
    api = FakeAviaApi(
        start_payload={"success": True},
        chunks=[chunk_builder()],
    )
    service = FlightSearchService(api)

    with caplog.at_level("ERROR"):
        response = await service.get_offers(pid="test")

    assert response.success is False
    assert response.result == {}
    assert "missing task_id" in caplog.text


@pytest.mark.asyncio
async def test_converter_exception_is_logged(chunk_builder, caplog) -> None:
    class FailingConverter(FlightOfferConverter):
        def convert_chunk(self, chunk: dict[str, Any]):
            raise RuntimeError("Forced failure")

    api = FakeAviaApi(
        start_payload={"success": True, "task_id": "task"},
        chunks=[chunk_builder()],
    )
    service = FlightSearchService(api, converter=FailingConverter())

    with caplog.at_level("ERROR"):
        response = await service.get_offers(pid="test")

    assert response.success is False
    assert response.result == {}
    assert "unexpected error converting chunk" in caplog.text
