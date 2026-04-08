from collections.abc import Iterable

from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.polymarket.models import GammaMarketDTO


def gamma_market_to_candidates(market: GammaMarketDTO) -> list[MarketCandidate]:
    if len(market.outcomes) != 2 or len(market.outcome_prices) != 2:
        return []

    if not market.active or market.closed:
        return []

    candidates: list[MarketCandidate] = []
    for outcome_label, implied_probability in zip(
        market.outcomes,
        market.outcome_prices,
        strict=True,
    ):
        candidates.append(
            MarketCandidate(
                market_id=market.market_id,
                event_id=market.event_id,
                market_title=market.question,
                outcome_label=outcome_label,
                sport_key=market.category.lower(),
                starts_at=market.starts_at,
                resolves_at=market.resolves_at,
                market_implied_probability=implied_probability,
                liquidity=market.liquidity,
            )
        )
    return candidates


def flatten_candidates(markets: Iterable[GammaMarketDTO]) -> list[MarketCandidate]:
    candidates: list[MarketCandidate] = []
    for market in markets:
        candidates.extend(gamma_market_to_candidates(market))
    return candidates
