"""Contracts for the external Avia API provider."""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any, Protocol, TypedDict


class StartSearchResponse(TypedDict, total=False):
    """Schema returned by AviaApi.start_search."""

    success: bool
    task_id: str
    error_message: str


ProviderChunk = dict[str, Any]


class AviaApiProtocol(Protocol):
    """Port describing interactions with the Avia API."""

    async def start_search(self) -> StartSearchResponse:
        """Start remote search and return metadata."""

    async def get_chunk(self, task_id: str) -> AsyncIterator[ProviderChunk]:
        """Yield chunked search results for the given task."""

