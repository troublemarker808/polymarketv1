from dataclasses import dataclass
from datetime import datetime, timedelta
from statistics import median

from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO
from pm_bot.strategy.event_identity_resolver import ResolvedReferenceEvent


@dataclass(frozen=True, slots=True)
class EstimatedWinProbability:
    fair_probability: float
    market_implied_probability: float
    source_kind: str
    source_timestamp: datetime | None
    staleness_seconds: int | None
    confidence_band: float
    is_tradeable: bool
    block_reason: str | None
    reference_event_id: str | None
    bookmaker_count: int

    @property
    def edge(self) -> float:
        return self.fair_probability - self.market_implied_probability


class ReferenceProbabilityAdapter:
    def __init__(
        self,
        *,
        max_staleness_minutes: int,
        minimum_bookmakers: int,
    ) -> None:
        self._max_staleness = timedelta(minutes=max_staleness_minutes)
        self._minimum_bookmakers = minimum_bookmakers

    def estimate(
        self,
        candidate: MarketCandidate,
        resolved_event: ResolvedReferenceEvent,
        reference_event: ReferenceOddsEventDTO,
        *,
        as_of: datetime,
    ) -> EstimatedWinProbability:
        bookmaker_probabilities: list[float] = []
        last_updates: list[datetime] = []

        for bookmaker in reference_event.bookmakers:
            market = next((market for market in bookmaker.markets if market.key == "h2h"), None)
            if market is None or len(market.outcomes) != 2:
                continue

            outcome_map = {outcome.name: outcome.price for outcome in market.outcomes}
            if candidate.outcome_label not in outcome_map:
                continue

            prices = list(outcome_map.values())
            if any(price <= 1.0 for price in prices):
                continue

            implied = [1.0 / price for price in prices]
            total = sum(implied)
            normalized = [value / total for value in implied]
            name_to_probability = {
                outcome.name: probability
                for outcome, probability in zip(market.outcomes, normalized, strict=True)
            }
            bookmaker_probabilities.append(name_to_probability[candidate.outcome_label])
            last_updates.append(market.last_update)

        if len(bookmaker_probabilities) < self._minimum_bookmakers:
            return _blocked_estimate(
                candidate,
                reason="insufficient_reference_bookmakers",
                reference_event_id=resolved_event.reference_event_id,
                bookmaker_count=len(bookmaker_probabilities),
            )

        latest_common_update = min(last_updates)
        staleness = as_of - latest_common_update
        if staleness > self._max_staleness:
            return _blocked_estimate(
                candidate,
                reason="reference_probability_stale",
                reference_event_id=resolved_event.reference_event_id,
                bookmaker_count=len(bookmaker_probabilities),
                source_timestamp=latest_common_update,
                staleness_seconds=int(staleness.total_seconds()),
            )

        fair_probability = float(median(bookmaker_probabilities))
        confidence_band = max(bookmaker_probabilities) - min(bookmaker_probabilities)
        estimate = EstimatedWinProbability(
            fair_probability=fair_probability,
            market_implied_probability=candidate.market_implied_probability,
            source_kind="the_odds_api_h2h_median",
            source_timestamp=latest_common_update,
            staleness_seconds=int(staleness.total_seconds()),
            confidence_band=confidence_band,
            is_tradeable=True,
            block_reason=None,
            reference_event_id=resolved_event.reference_event_id,
            bookmaker_count=len(bookmaker_probabilities),
        )
        return estimate


def _blocked_estimate(
    candidate: MarketCandidate,
    *,
    reason: str,
    reference_event_id: str | None,
    bookmaker_count: int,
    source_timestamp: datetime | None = None,
    staleness_seconds: int | None = None,
) -> EstimatedWinProbability:
    estimate = EstimatedWinProbability(
        fair_probability=0.0,
        market_implied_probability=candidate.market_implied_probability,
        source_kind="blocked",
        source_timestamp=source_timestamp,
        staleness_seconds=staleness_seconds,
        confidence_band=0.0,
        is_tradeable=False,
        block_reason=reason,
        reference_event_id=reference_event_id,
        bookmaker_count=bookmaker_count,
    )
    return estimate
