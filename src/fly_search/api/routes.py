"""API routes for the Fly Search service."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from av_parser.models import ServiceResponse
from fly_search.api.dependencies import (
    get_background_task_manager,
    get_cache_service,
    get_flight_service,
)
from fly_search.domain.services.background_task import TaskStatus
from fly_search.domain.services.flight_search import FlightSearchService
from fly_search.infrastructure.background_task_manager import (
    BackgroundTaskManager,
    TaskFailedError,
    TaskNotFoundError,
    TaskResultMissingError,
)
from fly_search.infrastructure.cache_service import CacheService

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
    cache: CacheService = Depends(get_cache_service),
) -> ServiceResponse:
    """
    Return normalized search results from provider.

    Results are cached for 3 minutes based on pid parameter.
    """
    # Строим ключ кеша с учётом pid
    cache_key = CacheService.build_cache_key("flights", pid=pid)

    # Пытаемся получить из кеша
    cached_response = cache.get_response(cache_key)
    if cached_response is not None:
        logger.info(
            "get_flights cache hit",
            extra={"event": "cache_hit", "pid": pid, "cache_key": cache_key},
        )
        return cached_response

    # Кеш промах - выполняем запрос
    logger.info("get_flights called", extra={"event": "call", "pid": pid})
    response = await service.get_offers(pid=pid)

    # Сохраняем в кеш
    cache.set_response(cache_key, response)

    logger.info(
        "get_flights finished",
        extra={
            "pid": response.pid,
            "success": response.success,
            "offers_count": sum(len(v) for v in response.result.values()),
            "cached": True,
        },
    )
    return response


@router.post("/start_search", tags=["tasks"])
async def start_search(
    pid: str | None = Query(
        default=None,
        description="External process identifier",
    ),
    task_manager: BackgroundTaskManager = Depends(get_background_task_manager),
) -> dict[str, str]:
    """
    Start background search task.

    Returns task_id that can be used to retrieve results via /get_result.
    """
    logger.info(
        "start_search called", extra={"event": "start_task", "pid": pid}
    )
    task_id = await task_manager.start_task(pid=pid)
    logger.info(
        "start_search finished",
        extra={"event": "task_started", "task_id": task_id, "pid": pid},
    )
    return {"task_id": task_id, "status": TaskStatus.PROCESSING}


@router.get("/get_result", tags=["tasks"])
async def get_result(
    task_id: str = Query(
        description="Task identifier returned by /start_search"
    ),
    task_manager: BackgroundTaskManager = Depends(get_background_task_manager),
) -> dict | ServiceResponse:
    """
    Get result of background search task.

    Returns task status and result (if completed) or error (if failed).
    """
    logger.info(
        "get_result called", extra={"event": "get_result", "task_id": task_id}
    )

    try:
        return task_manager.get_task_response(task_id)
    except TaskNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from None
    except TaskResultMissingError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None
    except TaskFailedError as e:
        raise HTTPException(status_code=500, detail=str(e)) from None

