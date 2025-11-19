"""Conversion utilities for transforming provider chunks into domain models."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from av_parser.models import (
    Baggage,
    BaggageInfo,
    Fare,
    FareInfo,
    FlightInfo,
    FlightOffer,
    FlightSegment,
    RuleInfo,
    Rules,
)

ProviderChunk = dict[str, Any]


@dataclass(slots=True)
class FlightOfferConverter:
    """Pure conversion helpers to keep service orchestration slim."""

    def convert_chunk(self, chunk: ProviderChunk) -> dict[str, list[FlightOffer]]:
        """Convert provider chunk into keyed offers dictionary."""
        if not chunk or "tickets" not in chunk:
            return {}

        agents = self._extract_agents(chunk)
        flight_legs = chunk.get("flight_legs", [])
        offers_by_key: dict[str, list[FlightOffer]] = defaultdict(list)

        for ticket in chunk.get("tickets", []):
            offer = self._build_offer(ticket, agents, flight_legs)
            if offer is None:
                continue
            route_key = self._build_route_key(offer)
            offers_by_key[route_key].append(offer)
        return offers_by_key

    def _build_offer(
        self,
        ticket: dict[str, Any],
        agents: dict[str, str],
        flight_legs: list[dict[str, Any]],
    ) -> FlightOffer | None:
        proposals = ticket.get("proposals", [])
        if not proposals:
            return None

        segments = self._build_segments(ticket, proposals, flight_legs)
        if not segments:
            return None

        fares = self._build_fares(proposals, agents)
        if not fares:
            return None

        prices = self._collect_prices(proposals, agents)
        min_provider, min_price = self._extract_min_price(prices)

        return FlightOffer(
            is_vtrip=self._is_vtrip(segments),
            key=ticket.get("signature") or ticket.get("hashsum") or ticket.get("id", ""),
            flight_info=FlightInfo(forward=segments),
            fares=fares,
            prices=prices,
            duration=sum(segment.duration for segment in segments),
            min_price=min_price,
            min_provider=min_provider,
        )

    def _build_segments(
        self,
        ticket: dict[str, Any],
        proposals: list[dict[str, Any]],
        flight_legs: list[dict[str, Any]],
    ) -> list[FlightSegment]:
        segments: list[FlightSegment] = []
        proposal_terms = proposals[0].get("flight_terms", {})
        for segment in ticket.get("segments", []):
            for flight_index in segment.get("flights", []):
                leg = self._safe_index(flight_legs, flight_index)
                if not leg:
                    continue
                term = proposal_terms.get(str(flight_index), {})
                segments.append(
                    FlightSegment(
                        departure=leg.get("origin", ""),
                        arrival=leg.get("destination", ""),
                        departure_date=self._format_date(leg.get("local_departure_date_time")),
                        arrival_date=self._format_date(leg.get("local_arrival_date_time")),
                        duration=self._compute_duration(
                            leg.get("departure_unix_timestamp"),
                            leg.get("arrival_unix_timestamp"),
                        ),
                        number=term.get("marketing_carrier_designator", {}).get("number", ""),
                        marketing_carrier=term.get("marketing_carrier_designator", {}).get(
                            "carrier", ""
                        ),
                        operating_carrier=leg.get("operating_carrier_designator", {}).get(
                            "carrier", ""
                        ),
                    )
                )
        return segments

    def _build_fares(
        self,
        proposals: list[dict[str, Any]],
        agents: dict[str, str],
    ) -> list[Fare]:
        fares: list[Fare] = []
        for proposal in proposals:
            min_fare = proposal.get("minimum_fare", {})
            trip_class = self._resolve_trip_class(proposal)
            agent_key = self._agent_key(str(proposal.get("agent_id")), agents)
            fare_info = FareInfo(
                fare_code=min_fare.get("fare_code") or min_fare.get("code", ""),
                trip_class=trip_class,
                baggage=self._build_baggage(min_fare),
                rules=self._build_rules(min_fare),
            )
            fares.append(
                Fare(
                    fare_key=min_fare.get("fare_key", ""),
                    fare_info=[fare_info],
                    prices={agent_key: int(proposal.get("price", {}).get("value", 0))},
                )
            )
        return fares

    def _collect_prices(
        self,
        proposals: list[dict[str, Any]],
        agents: dict[str, str],
    ) -> dict[str, int]:
        prices: dict[str, int] = {}
        for proposal in proposals:
            agent_id = str(proposal.get("agent_id"))
            agent_name = self._agent_key(agent_id, agents)
            prices[agent_name] = int(proposal.get("price", {}).get("value", 0))
        return prices

    def _extract_min_price(self, prices: dict[str, int]) -> tuple[str, int]:
        if not prices:
            return "", 0
        min_provider = min(prices, key=prices.get)
        return min_provider, prices[min_provider]

    @staticmethod
    def _compute_duration(departure_ts: Any, arrival_ts: Any) -> int:
        if not departure_ts or not arrival_ts:
            return 0
        return int((int(arrival_ts) - int(departure_ts)) / 60)

    @staticmethod
    def _is_vtrip(segments: Iterable[FlightSegment]) -> bool:
        segments = list(segments)
        if len(segments) <= 1:
            return False
        return any(seg.marketing_carrier != seg.operating_carrier for seg in segments)

    @staticmethod
    def _resolve_trip_class(proposal: dict[str, Any]) -> str:
        terms = proposal.get("flight_terms", {})
        first_term = next(iter(terms.values()), {})
        return first_term.get("trip_class", "")

    @staticmethod
    def _build_baggage(min_fare: dict[str, Any]) -> Baggage:
        handbags = min_fare.get("handbags") or {}
        baggage = min_fare.get("baggage") or {}
        return Baggage(
            handbags=BaggageInfo(
                count=int(handbags.get("count", 0)),
                weight=_int_or_none(handbags.get("weight")),
            ),
            baggage=BaggageInfo(
                count=int(baggage.get("count", 0)),
                weight=_int_or_none(baggage.get("weight")),
            ),
        )

    @staticmethod
    def _build_rules(min_fare: dict[str, Any]) -> Rules:
        return Rules(
            return_before_flight=_build_rule(min_fare.get("return_before_flight")),
            change_before_flight=_build_rule(min_fare.get("change_before_flight")),
        )

    @staticmethod
    def _format_date(value: Any) -> str:
        if not value:
            return ""
        if isinstance(value, str):
            return value.replace(" ", "T")
        if isinstance(value, int | float):
            return datetime.fromtimestamp(value, tz=UTC).isoformat()
        return str(value)

    @staticmethod
    def _build_route_key(offer: FlightOffer) -> str:
        if not offer.flight_info.forward:
            return ""
        first_segment = offer.flight_info.forward[0]
        departure_date = first_segment.departure_date[:10].replace("-", "")
        return f"{first_segment.departure}{first_segment.arrival}{departure_date}"

    @staticmethod
    def _extract_agents(chunk: ProviderChunk) -> dict[str, str]:
        agents = {}
        raw_agents = chunk.get("agents", {})
        for agent_id, agent_data in raw_agents.items():
            label = agent_data.get("label", {}).get("ru", {}).get("default")
            agents[str(agent_id)] = label or str(agent_id)
        return agents

    @staticmethod
    def _agent_key(agent_id: str, agents: dict[str, str]) -> str:
        return agents.get(agent_id, agent_id)

    @staticmethod
    def _safe_index(items: list[dict[str, Any]], index: int) -> dict[str, Any] | None:
        if index < 0 or index >= len(items):
            return None
        return items[index]


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _build_rule(data: dict[str, Any] | None) -> RuleInfo:
    if not data:
        return RuleInfo(available=False, is_from_config=False)
    return RuleInfo(
        available=bool(data.get("available")),
        is_from_config=bool(data.get("is_from_config")),
    )
