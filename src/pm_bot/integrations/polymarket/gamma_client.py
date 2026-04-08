import json
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import cast

import httpx

from pm_bot.integrations.polymarket.models import GammaMarketDTO, GammaSportDTO


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        msg = "expected datetime string from Gamma API"
        raise ValueError(msg)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    msg = f"expected numeric value, got {value!r}"
    raise ValueError(msg)


class GammaClient:
    def __init__(
        self,
        base_url: str,
        *,
        transport: httpx.BaseTransport | None = None,
        max_attempts: int = 3,
        retry_backoff_seconds: float = 0.5,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=10.0, transport=transport)
        self._max_attempts = max_attempts
        self._retry_backoff_seconds = retry_backoff_seconds

    def fetch_markets(self, *, limit: int) -> list[GammaMarketDTO]:
        payload = self._get_json(
            "/markets",
            params={
                "active": "true",
                "closed": "false",
                "limit": str(limit),
            },
        )
        if not isinstance(payload, list):
            msg = "Gamma API returned a non-list payload"
            raise ValueError(msg)
        return [parse_gamma_market(item) for item in payload]

    def fetch_sports_markets(
        self,
        *,
        sport_codes: set[str],
        events_limit_per_sport: int = 20,
    ) -> list[GammaMarketDTO]:
        if not sport_codes:
            return []

        payload = self._get_json("/sports")
        if not isinstance(payload, list):
            msg = "Gamma sports API returned a non-list payload"
            raise ValueError(msg)

        markets_by_id: dict[str, GammaMarketDTO] = {}
        for item in payload:
            sport = parse_gamma_sport(item)
            if sport.sport_code not in sport_codes or sport.discovery_tag is None:
                continue

            events_payload = self._get_json(
                "/events",
                params={
                    "tag_id": sport.discovery_tag,
                    "active": "true",
                    "closed": "false",
                    "limit": str(events_limit_per_sport),
                },
            )
            if not isinstance(events_payload, list):
                msg = "Gamma events API returned a non-list payload"
                raise ValueError(msg)

            for event in events_payload:
                for market in _parse_sports_event_markets(event):
                    markets_by_id.setdefault(market.market_id, market)
        return list(markets_by_id.values())

    def load_fixture(self, path: Path) -> list[GammaMarketDTO]:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            msg = "Gamma fixture must be a list"
            raise ValueError(msg)
        return [parse_gamma_market(item) for item in payload]

    def _get_json(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
    ) -> object:
        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            try:
                response = self._client.get(path, params=params)
                response.raise_for_status()
                return response.json()
            except (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError) as exc:
                last_error = exc
                if attempt >= self._max_attempts:
                    raise
                time.sleep(self._retry_backoff_seconds * attempt)
        if last_error is not None:
            raise last_error
        msg = "Gamma request failed without a captured exception"
        raise RuntimeError(msg)


def parse_gamma_market(value: object) -> GammaMarketDTO:
    if not isinstance(value, dict):
        msg = "Gamma market payload must be an object"
        raise ValueError(msg)

    outcomes = _parse_string_sequence(value.get("outcomes", []))
    outcome_prices = tuple(
        _parse_float(item) for item in _parse_sequence(value.get("outcomePrices", []))
    )

    return GammaMarketDTO(
        market_id=str(value["id"]),
        event_id=str(value.get("eventId", value["id"])),
        question=str(value["question"]),
        category=str(value.get("category", "")),
        active=bool(value.get("active", False)),
        closed=bool(value.get("closed", False)),
        liquidity=_parse_float(value.get("liquidityNum", value.get("liquidity", 0.0))),
        starts_at=_parse_datetime(value.get("gameStartTime", value.get("startDate"))),
        resolves_at=_parse_datetime(value.get("endDate")),
        outcomes=outcomes,
        outcome_prices=outcome_prices,
    )


def parse_gamma_sport(value: object) -> GammaSportDTO:
    if not isinstance(value, dict):
        msg = "Gamma sport payload must be an object"
        raise ValueError(msg)
    sport_code = str(value["sport"]).lower()
    tags = tuple(
        item.strip()
        for item in str(value.get("tags", "")).split(",")
        if item.strip()
    )
    discovery_tag = tags[1] if len(tags) >= 2 else None
    return GammaSportDTO(
        sport_code=sport_code,
        discovery_tag=discovery_tag,
    )


def _parse_sequence(value: object) -> Sequence[object]:
    if isinstance(value, str):
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return cast(Sequence[object], parsed)
    if not isinstance(value, list):
        msg = "expected sequence payload"
        raise ValueError(msg)
    return cast(Sequence[object], value)


def _parse_string_sequence(value: object) -> tuple[str, ...]:
    sequence = _parse_sequence(value)
    return tuple(str(item) for item in sequence)


def _parse_sports_event_markets(value: object) -> list[GammaMarketDTO]:
    if not isinstance(value, dict):
        return []

    markets = value.get("markets")
    if not isinstance(markets, list):
        return []

    parsed: list[GammaMarketDTO] = []
    for market in markets:
        if not isinstance(market, dict):
            continue
        event_id = value.get("id", market.get("eventId", market.get("id")))
        if event_id is None:
            continue
        event_title = value.get("title", market.get("question", ""))
        start_date = market.get(
            "gameStartTime",
            market.get("startDate", value.get("startDate")),
        )
        end_date = market.get(
            "endDate",
            value.get("endDate", market.get("gameStartTime", value.get("startDate"))),
        )
        enriched_market = {
            **market,
            "eventId": str(event_id),
            "question": market.get("question", event_title),
            "category": "sports",
            "startDate": start_date,
            "endDate": end_date,
        }
        try:
            parsed.append(parse_gamma_market(enriched_market))
        except (KeyError, ValueError, TypeError):
            continue
    return parsed
