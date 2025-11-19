"""Application service orchestrating communication with Avia API."""

from __future__ import annotations

import logging
from uuid import uuid4

from av_parser.models import FlightOffer, ServiceResponse

from ..ports.avia_api import AviaApiProtocol, ProviderChunk
from .converter import FlightOfferConverter

logger = logging.getLogger(__name__)


class FlightSearchService:
    """Fetch and adapt search results from the Avia API provider."""

    def __init__(
        self,
        avia_api: AviaApiProtocol,
        converter: FlightOfferConverter | None = None,
    ) -> None:
        self._avia_api = avia_api
        self._converter = converter or FlightOfferConverter()

    async def get_offers(self, pid: str | None = None) -> ServiceResponse:
        """Execute search and return normalized response."""
        process_id = pid or self._generate_pid()
        start_response = await self._avia_api.start_search()
        logger.info("start_search finished", extra={"pid": process_id, "response": start_response})

        if not start_response.get("success"):
            logger.error("start_search failed", extra={"pid": process_id})
            return ServiceResponse(success=False, pid=process_id, result={})

        task_id = start_response.get("task_id")
        if not task_id:
            logger.error("start_search missing task_id", extra={"pid": process_id})
            return ServiceResponse(success=False, pid=process_id, result={})

        aggregated: dict[str, list[FlightOffer]] = {}
        async for chunk in self._avia_api.get_chunk(task_id):
            offers = self._convert_chunk(chunk)
            aggregated = self._merge_offers(aggregated, offers)
            logger.debug(
                "chunk processed",
                extra={"pid": process_id, "chunk_offers": sum(len(v) for v in offers.values())},
            )

        success = any(aggregated.values())
        return ServiceResponse(success=success, pid=process_id, result=aggregated)

    def _convert_chunk(self, chunk: ProviderChunk) -> dict[str, list[FlightOffer]]:
        try:
            return self._converter.convert_chunk(chunk)
        except Exception:
            logger.exception("failed to convert chunk")
            return {}

    @staticmethod
    def _merge_offers(
        target: dict[str, list[FlightOffer]],
        new: dict[str, list[FlightOffer]],
    ) -> dict[str, list[FlightOffer]]:
        for key, offers in new.items():
            if key not in target:
                target[key] = []
            target[key].extend(offers)
        return target

    @staticmethod
    def _generate_pid() -> str:
        return uuid4().hex
