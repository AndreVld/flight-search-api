"""Dependency wiring for FastAPI endpoints."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from fly_search.domain.ports.avia_api import AviaApiProtocol
from fly_search.domain.services.background_task import BackgroundTaskService
from fly_search.domain.services.converter import FlightOfferConverter
from fly_search.domain.services.flight_search import FlightSearchService
from fly_search.infrastructure.avia_api_adapter import AviaApiAdapter
from fly_search.infrastructure.background_task_manager import BackgroundTaskManager
from fly_search.infrastructure.cache_service import CacheService


@lru_cache(maxsize=1)
def get_converter() -> FlightOfferConverter:
    return FlightOfferConverter()


def get_avia_api() -> AviaApiProtocol:
    """Return adapter wrapping AviaApi to conform to protocol."""
    return AviaApiAdapter()


@lru_cache(maxsize=1)
def get_cache_service() -> CacheService:
    """Return cache service instance (singleton)."""
    return CacheService()


def get_flight_service(
    avia_api: AviaApiProtocol = Depends(get_avia_api),
    converter: FlightOfferConverter = Depends(get_converter),
) -> FlightSearchService:
    """Assemble the domain service."""
    return FlightSearchService(avia_api=avia_api, converter=converter)


def get_background_task_service(
    flight_service: FlightSearchService = Depends(get_flight_service),
) -> BackgroundTaskService:
    """Assemble background task service."""
    return BackgroundTaskService(flight_search_service=flight_service)


def get_background_task_manager(
    task_service: BackgroundTaskService = Depends(get_background_task_service),
    cache_service: CacheService = Depends(get_cache_service),
) -> BackgroundTaskManager:
    """Assemble background task manager."""
    return BackgroundTaskManager(task_service=task_service, cache_service=cache_service)
