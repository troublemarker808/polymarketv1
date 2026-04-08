from datetime import UTC, datetime

from pm_bot.integrations.polymarket.models import GammaMarketDTO
from pm_bot.integrations.polymarket.translators import gamma_market_to_candidates


def test_gamma_market_to_candidates_expands_binary_market() -> None:
    market = GammaMarketDTO(
        market_id="market-1",
        event_id="event-1",
        question="Will Team A win?",
        category="Sports",
        active=True,
        closed=False,
        liquidity=120000.0,
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        outcomes=("Team A", "Team B"),
        outcome_prices=(0.62, 0.38),
    )

    candidates = gamma_market_to_candidates(market)

    assert len(candidates) == 2
    assert candidates[0].market_title == "Will Team A win?"
    assert candidates[1].market_implied_probability == 0.38
