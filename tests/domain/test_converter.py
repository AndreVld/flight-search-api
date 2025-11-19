"""Tests for FlightOfferConverter."""

from __future__ import annotations

from av_parser.models import FlightOffer
from fly_search.domain.services.converter import FlightOfferConverter


def test_converter_produces_offer(chunk_builder) -> None:
    chunk = chunk_builder()
    converter = FlightOfferConverter()

    result = converter.convert_chunk(chunk)

    assert "MOWLED20251217" in result
    offers = result["MOWLED20251217"]
    assert len(offers) == 1
    offer: FlightOffer = offers[0]
    assert offer.flight_info.forward[0].departure == "MOW"
    assert offer.flight_info.forward[0].arrival == "LED"
    assert offer.min_price == 1592
    assert offer.min_provider == "OneTwoTrip"
    assert offer.is_vtrip is False


def test_converter_detects_vtrip(chunk_builder) -> None:
    chunk = chunk_builder()
    # add second leg with different operating carrier
    chunk["flight_legs"].append(
        {
            "origin": "LED",
            "destination": "MOW",
            "local_departure_date_time": "2025-12-18 10:00",
            "local_arrival_date_time": "2025-12-18 12:00",
            "departure_unix_timestamp": 1766042400,
            "arrival_unix_timestamp": 1766049600,
            "operating_carrier_designator": {"carrier": "A4"},
        }
    )
    chunk["tickets"][0]["segments"][0]["flights"] = [0, 1]
    chunk["tickets"][0]["proposals"][0]["flight_terms"]["1"] = {
        "trip_class": "Y",
        "marketing_carrier_designator": {"carrier": "R0", "number": "123"},
    }
    converter = FlightOfferConverter()

    offers = converter.convert_chunk(chunk)["MOWLED20251217"]

    assert offers[0].is_vtrip is True

