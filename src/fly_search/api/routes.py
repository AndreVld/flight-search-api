"""API routes for the Fly Search service."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query

from av_parser.models import ServiceResponse
from fly_search.api.dependencies import get_flight_service
from fly_search.domain.services.flight_search import FlightSearchService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/get_flights",
    response_model=ServiceResponse,
    response_model_exclude_none=True,
    tags=["flights"],
)
async def get_flights(
    pid: str | None = Query(
        default=None,
        description="External process identifier"),
    service: FlightSearchService = Depends(get_flight_service),
) -> ServiceResponse:
    """Return normalized search results from provider."""
    logger.info("get_flights called", extra={"event": "call", "pid": pid})
    response = await service.get_offers(pid=pid)
    logger.info(
        "get_flights finished",
        extra={
            "pid": response.pid,
            "success": response.success,
            "offers_count": sum(len(v) for v in response.result.values()),
        },
    )
    return response

