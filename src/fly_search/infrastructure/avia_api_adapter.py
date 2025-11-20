"""Adapter wrapping AviaApi implementation to conform to AviaApiProtocol."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncIterator

from av_parser.api_service import AviaApi

from ..domain.ports.avia_api import ProviderChunk, StartSearchResponse

logger = logging.getLogger(__name__)


class AviaApiAdapter:
    """
    Adapter wrapping AviaApi implementation to conform to the protocol.

    Note: AviaApi.get_chunk() uses blocking sleep(15) which blocks the event loop.
    This adapter isolates it in a separate thread.

    Thread limiting: Uses Semaphore to limit the number of concurrent generator
    threads (configurable via settings).
    """

    _thread_semaphore: asyncio.Semaphore | None = None

    def __init__(
        self,
        avia_api: AviaApi | None = None,
        max_threads: int | None = None,
        chunk_queue_timeout: float | None = None,
        thread_join_timeout: float | None = None,
    ) -> None:
        """
        Initialize adapter with optional AviaApi instance.

        Args:
            avia_api: AviaApi instance to use
            max_threads: Maximum number of concurrent threads
            chunk_queue_timeout: Timeout for getting chunk from queue
            thread_join_timeout: Timeout for waiting thread completion
        """
        from fly_search.config import get_settings

        self._api = avia_api or AviaApi()
        settings = get_settings()

        # Используем переданные значения или значения из конфига
        self._max_threads = (
            max_threads if max_threads is not None else settings.max_concurrent_threads
        )
        self._chunk_queue_timeout = (
            chunk_queue_timeout if chunk_queue_timeout is not None else settings.chunk_queue_timeout
        )
        self._thread_join_timeout = (
            thread_join_timeout if thread_join_timeout is not None else settings.thread_join_timeout
        )

        if AviaApiAdapter._thread_semaphore is None:
            AviaApiAdapter._thread_semaphore = asyncio.Semaphore(self._max_threads)

    async def start_search(self) -> StartSearchResponse:
        """Start search and return metadata."""
        try:
            result = await self._api.start_search()
            return StartSearchResponse(
                success=result.get("success", False),
                task_id=result.get("task_id", ""),
                error_message=result.get("error_message", ""),
            )
        except Exception as e:
            logger.error("Failed to start search", exc_info=True, extra={"error": str(e)})
            return StartSearchResponse(
                success=False,
                task_id="",
                error_message=str(e),
            )

    async def get_chunk(self, task_id: str) -> AsyncIterator[ProviderChunk]:
        """
        Yield search result chunks for the given task.

        Runs async generator in a separate thread to completely isolate
        blocking sleep(15) from the event loop. This allows FastAPI to handle
        other requests (including healthcheck) while waiting for chunks.
        """
        import queue as std_queue
        import threading

        # Используем стандартную очередь для потокобезопасной передачи данных между потоками
        chunk_queue: std_queue.Queue[ProviderChunk | Exception | None] = std_queue.Queue()
        gen = self._api.get_chunk(task_id)
        thread_error: Exception | None = None

        def _run_generator_in_thread() -> None:
            """Run async generator in separate thread to isolate blocking sleep."""
            nonlocal thread_error
            loop: asyncio.AbstractEventLoop | None = None
            try:
                # Создаём новый event loop для этого потока
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

                async def _consume_generator() -> None:
                    """Consume generator and put chunks into queue."""
                    try:
                        async for chunk in gen:
                            # Фильтруем пустые чанки
                            if chunk:
                                chunk_queue.put(chunk)
                    except Exception as e:
                        logger.error(
                            "Error processing chunk in thread",
                            exc_info=True,
                            extra={"task_id": task_id, "error": str(e)},
                        )
                        chunk_queue.put(e)
                    finally:
                        chunk_queue.put(None)  # Сигнал завершения

                # Запускаем async generator в event loop потока
                loop.run_until_complete(_consume_generator())
            except Exception as e:
                logger.error(
                    "Critical error in generator thread",
                    exc_info=True,
                    extra={"task_id": task_id, "error": str(e)},
                )
                thread_error = e
                chunk_queue.put(e)
            finally:
                # Закрываем event loop
                if loop is not None:
                    try:
                        # Отменяем все незавершённые задачи
                        pending = asyncio.all_tasks(loop)
                        for task in pending:
                            task.cancel()
                        # Ждём завершения отменённых задач
                        if pending:
                            loop.run_until_complete(
                                asyncio.gather(*pending, return_exceptions=True)
                            )
                    except Exception as e:
                        logger.warning("Error cancelling tasks in thread", extra={"error": str(e)})
                    finally:
                        try:
                            loop.close()
                        except Exception as e:
                            logger.warning(
                                "Error closing event loop", extra={"error": str(e)}
                            )

        # Запускаем генератор в отдельном потоке (daemon, чтобы не блокировать завершение)
        # threading.Thread используется вместо asyncio.to_thread() потому что:
        # 1. to_thread() ждёт завершения, а нам нужен streaming
        # 2. Нужно отдавать чанки по мере поступления через очередь
        # 3. Semaphore ограничивает количество одновременных потоков

        # Получаем доступ к Semaphore (ограничение потоков)
        semaphore = AviaApiAdapter._thread_semaphore
        if semaphore is None:
            semaphore = asyncio.Semaphore(self._max_threads)
            AviaApiAdapter._thread_semaphore = semaphore

        # Ждём доступного слота в Semaphore перед созданием потока
        await semaphore.acquire()

        thread = threading.Thread(target=_run_generator_in_thread, daemon=True)
        thread.start()

        try:
            while True:
                # Ждём чанк с периодической отдачей управления event loop
                try:
                    chunk = chunk_queue.get(timeout=self._chunk_queue_timeout)
                except std_queue.Empty:
                    # Отдаём управление event loop для обработки других запросов
                    await asyncio.sleep(0)
                    continue

                if chunk is None:
                    # Генератор завершился
                    break

                if isinstance(chunk, Exception):
                    # Пробрасываем исключение из потока
                    logger.error(
                        "Exception from generator thread",
                        exc_info=True,
                        extra={"task_id": task_id, "error": str(chunk)},
                    )
                    raise chunk

                yield chunk

                # Проверяем ошибки потока после yield
                if thread_error:
                    raise thread_error

        except asyncio.CancelledError:
            # Запрос был отменён - логируем и пробрасываем дальше
            logger.info("Chunk request was cancelled", extra={"task_id": task_id})
            raise
        except Exception as e:
            # Логируем неожиданные ошибки
            logger.error(
                "Unexpected error while getting chunks",
                exc_info=True,
                extra={"task_id": task_id, "error": str(e)},
            )
            raise
        finally:
            # Ждём завершения потока (с таймаутом)
            thread.join(timeout=self._thread_join_timeout)
            if thread.is_alive():
                logger.warning(
                    "Generator thread did not finish within timeout",
                    extra={"task_id": task_id},
                )
            # Освобождаем Semaphore после завершения (или таймаута)
            try:
                semaphore.release()
            except Exception as e:
                logger.warning(
                    "Error releasing semaphore",
                    extra={"task_id": task_id, "error": str(e)},
                )
