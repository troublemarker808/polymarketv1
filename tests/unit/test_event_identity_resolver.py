from datetime import UTC, datetime

from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.reference_odds.models import ReferenceBookmakerDTO, ReferenceOddsEventDTO
from pm_bot.strategy.event_identity_resolver import EventIdentityResolver


def test_event_identity_resolver_matches_unique_event() -> None:
    candidate = MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.6,
        liquidity=50000.0,
    )
    event = ReferenceOddsEventDTO(
        event_id="ref-1",
        sport_key="soccer_epl",
        commence_time=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
        home_team="Team A",
        away_team="Team B",
        bookmakers=tuple[ReferenceBookmakerDTO, ...](),
    )

    result = EventIdentityResolver(match_window_minutes=90).resolve(candidate, [event])

    assert result.resolved_event is not None
    assert result.resolved_event.reference_event_id == "ref-1"


def test_event_identity_resolver_blocks_ambiguous_matches() -> None:
    candidate = MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.6,
        liquidity=50000.0,
    )
    events = [
        ReferenceOddsEventDTO(
            event_id="ref-1",
            sport_key="soccer_epl",
            commence_time=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
            home_team="Team A",
            away_team="Team B",
            bookmakers=tuple[ReferenceBookmakerDTO, ...](),
        ),
        ReferenceOddsEventDTO(
            event_id="ref-2",
            sport_key="soccer_epl",
            commence_time=datetime(2026, 4, 8, 9, 15, tzinfo=UTC),
            home_team="Team A",
            away_team="Team B",
            bookmakers=tuple[ReferenceBookmakerDTO, ...](),
        ),
    ]

    result = EventIdentityResolver(match_window_minutes=90).resolve(candidate, events)

    assert result.resolved_event is None
    assert result.block_reason == "reference_event_ambiguous"


def test_event_identity_resolver_matches_last_name_outcome_labels() -> None:
    candidate = MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Rolex Monte Carlo Masters: Jiri Lehecka vs Alejandro Tabilo",
        outcome_label="Lehecka",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.6,
        liquidity=50000.0,
    )
    event = ReferenceOddsEventDTO(
        event_id="ref-1",
        sport_key="tennis_atp_monte_carlo_masters",
        commence_time=datetime(2026, 4, 8, 9, 30, tzinfo=UTC),
        home_team="Jiri Lehecka",
        away_team="Alejandro Tabilo",
        bookmakers=tuple[ReferenceBookmakerDTO, ...](),
    )

    result = EventIdentityResolver(match_window_minutes=90).resolve(candidate, [event])

    assert result.resolved_event is not None
    assert result.resolved_event.reference_event_id == "ref-1"
