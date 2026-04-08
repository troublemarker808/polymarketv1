from collections.abc import Sequence
from datetime import datetime

from pm_bot.integrations.reference_odds.models import (
    ReferenceBookmakerDTO,
    ReferenceMarketDTO,
    ReferenceOddsEventDTO,
    ReferenceOutcomeDTO,
)


def parse_reference_event(value: object) -> ReferenceOddsEventDTO:
    if not isinstance(value, dict):
        msg = "reference event payload must be an object"
        raise ValueError(msg)

    bookmakers = tuple(
        parse_bookmaker(item)
        for item in _parse_sequence(value.get("bookmakers", []))
    )
    return ReferenceOddsEventDTO(
        event_id=str(value["id"]),
        sport_key=str(value["sport_key"]),
        commence_time=_parse_datetime(value["commence_time"]),
        home_team=str(value["home_team"]),
        away_team=str(value["away_team"]),
        bookmakers=bookmakers,
    )


def parse_bookmaker(value: object) -> ReferenceBookmakerDTO:
    if not isinstance(value, dict):
        msg = "bookmaker payload must be an object"
        raise ValueError(msg)
    markets = tuple(parse_market(item) for item in _parse_sequence(value.get("markets", [])))
    return ReferenceBookmakerDTO(
        key=str(value["key"]),
        title=str(value.get("title", value["key"])),
        markets=markets,
    )


def parse_market(value: object) -> ReferenceMarketDTO:
    if not isinstance(value, dict):
        msg = "market payload must be an object"
        raise ValueError(msg)
    outcomes = tuple(parse_outcome(item) for item in _parse_sequence(value.get("outcomes", [])))
    return ReferenceMarketDTO(
        key=str(value["key"]),
        last_update=_parse_datetime(value["last_update"]),
        outcomes=outcomes,
    )


def parse_outcome(value: object) -> ReferenceOutcomeDTO:
    if not isinstance(value, dict):
        msg = "outcome payload must be an object"
        raise ValueError(msg)
    return ReferenceOutcomeDTO(
        name=str(value["name"]),
        price=_parse_float(value["price"]),
    )


def _parse_sequence(value: object) -> Sequence[object]:
    if not isinstance(value, list):
        msg = "expected sequence payload"
        raise ValueError(msg)
    return value


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        msg = "expected datetime string"
        raise ValueError(msg)
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    msg = f"expected numeric price, got {value!r}"
    raise ValueError(msg)
