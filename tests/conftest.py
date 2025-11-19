"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from typing import Any

import pytest

BASE_CHUNK: dict[str, Any] = {
    "tickets": [
        {
            "id": "ticket-1",
            "signature": "SIG-1",
            "segments": [{"flights": [0], "tags": [], "transfers": []}],
            "proposals": [
                {
                    "agent_id": 344,
                    "price": {"value": 1592},
                    "minimum_fare": {
                        "fare_key": "fare-key",
                        "fare_code": "Y_1PC36",
                        "handbags": {"count": 1},
                        "baggage": {"count": 1, "weight": 36},
                        "return_before_flight": {"available": True, "is_from_config": True},
                        "change_before_flight": {"available": False, "is_from_config": True},
                    },
                    "flight_terms": {
                        "0": {
                            "trip_class": "Y",
                            "marketing_carrier_designator": {"carrier": "R0", "number": "772"},
                        }
                    },
                }
            ],
        }
    ],
    "flight_legs": [
        {
            "origin": "MOW",
            "destination": "LED",
            "local_departure_date_time": "2025-12-17 15:30",
            "local_arrival_date_time": "2025-12-17 19:26",
            "departure_unix_timestamp": 1765985400,
            "arrival_unix_timestamp": 1765999560,
            "operating_carrier_designator": {"carrier": "R0"},
        }
    ],
    "agents": {
        "344": {"label": {"ru": {"default": "OneTwoTrip"}}},
    },
}


@pytest.fixture
def chunk_builder() -> Callable[[], dict[str, Any]]:
    """Return a factory that produces independent copies of the sample chunk."""

    def _builder() -> dict[str, Any]:
        return deepcopy(BASE_CHUNK)

    return _builder

