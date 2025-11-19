"""Dependency wiring for FastAPI endpoints."""

from __future__ import annotations

from functools import lru_cache

from fastapi import Depends

from fly_search.domain.ports.avia_api import AviaApiProtocol
from fly_search.domain.services.converter import FlightOfferConverter
from fly_search.domain.services.flight_search import FlightSearchService
from fly_search.infrastructure.avia_api_adapter import AviaApiAdapter


@lru_cache(maxsize=1)
def get_converter() -> FlightOfferConverter:
    return FlightOfferConverter()


def get_avia_api() -> AviaApiProtocol:
    """Return adapter wrapping AviaApi to conform to protocol."""
    return AviaApiAdapter()


def get_flight_service(
    avia_api: AviaApiProtocol = Depends(get_avia_api),
    converter: FlightOfferConverter = Depends(get_converter),
) -> FlightSearchService:
    """Assemble the domain service."""
    return FlightSearchService(avia_api=avia_api, converter=converter)
