"""Background task manager for processing and storing task results."""

from __future__ import annotations

import asyncio
import logging

from av_parser.models import ServiceResponse

from ..domain.services.background_task import BackgroundTaskService, TaskStatus
from .cache_service import CacheService

logger = logging.getLogger(__name__)


class TaskNotFoundError(Exception):
    """Raised when task is not found in cache."""

    pass


class TaskFailedError(Exception):
    """Raised when task execution failed."""

    def __init__(self, error: str) -> None:
        """
        Initialize task failed error.

        Args:
            error: Error message from task execution
        """
        self.error = error
        super().__init__(f"Task failed: {error}")


class TaskResultMissingError(Exception):
    """Raised when task completed but result is missing."""

    pass


class BackgroundTaskManager:
    """
    Manager for background tasks with result caching.

    Coordinates task execution and result storage using CacheService.
    """

    def __init__(
        self,
        task_service: BackgroundTaskService,
        cache_service: CacheService,
    ) -> None:
        """
        Initialize task manager.

        Args:
            task_service: Service for executing searches
            cache_service: Service for caching task results
        """
        self._task_service = task_service
        self._cache_service = cache_service

    async def start_task(self, pid: str | None = None) -> str:
        """
        Start background search task.

        Args:
            pid: Optional process identifier

        Returns:
            Task ID for tracking
        """
        task_id = await self._task_service.start_task(pid=pid)

        # Сохраняем задачу в кеш со статусом processing
        self._cache_service.set_task(
            task_id,
            {
                "status": TaskStatus.PROCESSING,
                "pid": pid,
                "result": None,
                "error": None,
            },
        )

        # Запускаем обработку в фоне
        asyncio.create_task(self._process_task(task_id, pid))

        return task_id

    async def _process_task(self, task_id: str, pid: str | None) -> None:
        """
        Process task in background and store result.

        Args:
            task_id: Task identifier
            pid: Optional process identifier
        """
        try:
            # Выполняем поиск
            result = await self._task_service.execute_search(task_id, pid)

            # Сохраняем успешный результат
            self._cache_service.set_task(
                task_id,
                {
                    "status": TaskStatus.COMPLETED,
                    "pid": result.pid,
                    "result": result,
                    "error": None,
                },
            )

            logger.info(
                "Task processing completed",
                extra={
                    "task_id": task_id,
                    "status": TaskStatus.COMPLETED,
                    "success": result.success,
                },
            )

        except Exception as e:
            # Сохраняем ошибку
            self._cache_service.set_task(
                task_id,
                {
                    "status": TaskStatus.FAILED,
                    "pid": pid,
                    "result": None,
                    "error": str(e),
                },
            )

            logger.error(
                "Task processing failed",
                extra={
                    "task_id": task_id,
                    "status": TaskStatus.FAILED,
                    "error": str(e),
                },
                exc_info=True,
            )

    def get_task_result(self, task_id: str) -> dict | None:
        """
        Get task result from cache.

        Args:
            task_id: Task identifier

        Returns:
            Task data dict or None if not found
        """
        return self._cache_service.get_task(task_id)

    def get_task_response(self, task_id: str) -> dict | ServiceResponse:
        """
        Get task response with proper status handling.

        Handles all task statuses and returns appropriate response.

        Returns appropriate response or raises exceptions.

        Args:
            task_id: Task identifier

        Returns:
            Response dict for PROCESSING status or ServiceResponse for COMPLETED

        Raises:
            TaskNotFoundError: If task is not found in cache
            TaskResultMissingError: If task completed but result is missing
            TaskFailedError: If task execution failed
        """
        task_data = self.get_task_result(task_id)

        if task_data is None:
            logger.warning("Task not found", extra={"task_id": task_id})
            raise TaskNotFoundError(f"Task {task_id} not found")

        status = task_data.get("status")

        if status == TaskStatus.PROCESSING:
            logger.info("Task still processing", extra={"task_id": task_id})
            return {
                "task_id": task_id,
                "status": TaskStatus.PROCESSING,
                "pid": task_data.get("pid"),
            }

        if status == TaskStatus.COMPLETED:
            result = task_data.get("result")
            if result is None:
                logger.error(
                    "Task completed but result is missing",
                    extra={"task_id": task_id},
                )
                raise TaskResultMissingError(
                    f"Task {task_id} completed but result is missing"
                )

            logger.info(
                "Task result retrieved",
                extra={
                    "task_id": task_id,
                    "status": TaskStatus.COMPLETED,
                    "success": result.success,
                },
            )
            return result

        if status == TaskStatus.FAILED:
            error = task_data.get("error", "Unknown error")
            logger.warning("Task failed", extra={"task_id": task_id, "error": error})
            raise TaskFailedError(error)

        logger.error(
            "Unknown task status",
            extra={"task_id": task_id, "status": status},
        )
        raise ValueError(f"Unknown task status: {status}")


