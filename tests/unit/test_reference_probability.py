from datetime import UTC, datetime, timedelta

from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.reference_odds.models import (
    ReferenceBookmakerDTO,
    ReferenceMarketDTO,
    ReferenceOddsEventDTO,
    ReferenceOutcomeDTO,
)
from pm_bot.strategy.event_identity_resolver import ResolvedReferenceEvent
from pm_bot.strategy.reference_probability import ReferenceProbabilityAdapter


def _reference_event(last_update: datetime) -> ReferenceOddsEventDTO:
    market = ReferenceMarketDTO(
        key="h2h",
        last_update=last_update,
        outcomes=(
            ReferenceOutcomeDTO(name="Team A", price=1.5),
            ReferenceOutcomeDTO(name="Team B", price=2.7),
        ),
    )
    bookmakers = tuple(
        ReferenceBookmakerDTO(key=f"book-{index}", title=f"Book {index}", markets=(market,))
        for index in range(3)
    )
    return ReferenceOddsEventDTO(
        event_id="ref-1",
        sport_key="soccer_epl",
        commence_time=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        home_team="Team A",
        away_team="Team B",
        bookmakers=bookmakers,
    )


def test_reference_probability_returns_tradeable_estimate() -> None:
    candidate = MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.61,
        liquidity=120000.0,
    )
    adapter = ReferenceProbabilityAdapter(max_staleness_minutes=20, minimum_bookmakers=3)

    estimate = adapter.estimate(
        candidate,
        ResolvedReferenceEvent(
            reference_event_id="ref-1",
            matched_home="Team A",
            matched_away="Team B",
            matched_start_time=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            match_rule_version="v1",
        ),
        _reference_event(datetime(2026, 4, 8, 8, 55, tzinfo=UTC)),
        as_of=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
    )

    assert estimate.is_tradeable is True
    assert estimate.edge > 0.0


def test_reference_probability_blocks_stale_input() -> None:
    candidate = MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.61,
        liquidity=120000.0,
    )
    adapter = ReferenceProbabilityAdapter(max_staleness_minutes=20, minimum_bookmakers=3)

    estimate = adapter.estimate(
        candidate,
        ResolvedReferenceEvent(
            reference_event_id="ref-1",
            matched_home="Team A",
            matched_away="Team B",
            matched_start_time=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
            match_rule_version="v1",
        ),
        _reference_event(datetime(2026, 4, 8, 8, 0, tzinfo=UTC)),
        as_of=datetime(2026, 4, 8, 10, 0, tzinfo=UTC) + timedelta(hours=1),
    )

    assert estimate.is_tradeable is False
    assert estimate.block_reason == "reference_probability_stale"
