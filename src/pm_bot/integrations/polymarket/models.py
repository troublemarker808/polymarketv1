from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class GammaMarketDTO:
    market_id: str
    event_id: str
    question: str
    category: str
    active: bool
    closed: bool
    liquidity: float
    starts_at: datetime
    resolves_at: datetime
    outcomes: tuple[str, ...]
    outcome_prices: tuple[float, ...]


@dataclass(frozen=True, slots=True)
class GammaSportDTO:
    sport_code: str
    discovery_tag: str | None
