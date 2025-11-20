"""Background task service for asynchronous flight search processing."""

from __future__ import annotations

import logging
from uuid import uuid4

from av_parser.models import ServiceResponse

from .flight_search import FlightSearchService

logger = logging.getLogger(__name__)


class TaskStatus:
    """Task status constants."""

    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class BackgroundTaskService:
    """
    Service for managing background flight search tasks.

    Handles task lifecycle: creation, execution, and result storage.
    """

    def __init__(
        self,
        flight_search_service: FlightSearchService,
    ) -> None:
        """
        Initialize background task service.

        Args:
            flight_search_service: Service for executing flight searches
        """
        self._flight_search_service = flight_search_service

    async def start_task(self, pid: str | None = None) -> str:
        """
        Start background search task.

        Args:
            pid: Optional process identifier

        Returns:
            Task ID for tracking the task
        """
        task_id = str(uuid4())

        logger.info(
            "Background task started",
            extra={"task_id": task_id, "pid": pid, "status": TaskStatus.PROCESSING},
        )

        return task_id

    async def execute_search(self, task_id: str, pid: str | None) -> ServiceResponse:
        """
        Execute search and return result.

        Args:
            task_id: Task identifier
            pid: Optional process identifier

        Returns:
            Search result
        """
        try:
            result = await self._flight_search_service.get_offers(pid=pid)
            logger.info(
                "Background task completed",
                extra={
                    "task_id": task_id,
                    "pid": result.pid,
                    "success": result.success,
                },
            )
            return result
        except Exception as e:
            logger.error(
                "Background task failed",
                extra={"task_id": task_id, "error": str(e)},
                exc_info=True,
            )
            raise

