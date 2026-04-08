from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ReferenceOutcomeDTO:
    name: str
    price: float


@dataclass(frozen=True, slots=True)
class ReferenceMarketDTO:
    key: str
    last_update: datetime
    outcomes: tuple[ReferenceOutcomeDTO, ...]


@dataclass(frozen=True, slots=True)
class ReferenceBookmakerDTO:
    key: str
    title: str
    markets: tuple[ReferenceMarketDTO, ...]


@dataclass(frozen=True, slots=True)
class ReferenceOddsEventDTO:
    event_id: str
    sport_key: str
    commence_time: datetime
    home_team: str
    away_team: str
    bookmakers: tuple[ReferenceBookmakerDTO, ...]
