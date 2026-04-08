from datetime import UTC, datetime, timedelta

from pm_bot.domain.models import MarketCandidate
from pm_bot.strategy.market_selector import DEFAULT_OBSERVE_ONLY_REASON, MarketSelector


def _candidate(
    *,
    outcome_label: str,
    starts_in_hours: int = 24,
    resolves_in_hours: int = 36,
    sport_key: str = "sports",
) -> MarketCandidate:
    now = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    return MarketCandidate(
        market_id=f"market-{outcome_label}",
        event_id=f"event-{outcome_label}",
        market_title="Example",
        outcome_label=outcome_label,
        sport_key=sport_key,
        starts_at=now + timedelta(hours=starts_in_hours),
        resolves_at=now + timedelta(hours=resolves_in_hours),
        market_implied_probability=0.6,
        liquidity=50000.0,
    )


def test_selector_keeps_short_window_sports_candidates_as_observe_only() -> None:
    selector = MarketSelector(candidate_window_hours=72)
    as_of = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)

    selected = selector.select(
        [_candidate(outcome_label="Team A", starts_in_hours=24, resolves_in_hours=36)],
        as_of=as_of,
    )

    assert len(selected) == 1
    assert selected[0].observe_only_reason == DEFAULT_OBSERVE_ONLY_REASON


def test_selector_filters_non_sports_long_window_and_draw_markets() -> None:
    selector = MarketSelector(candidate_window_hours=72)
    as_of = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    candidates = [
        _candidate(outcome_label="Draw", starts_in_hours=24, resolves_in_hours=36),
        _candidate(outcome_label="Team A", starts_in_hours=120, resolves_in_hours=132),
        _candidate(
            outcome_label="Team A",
            starts_in_hours=24,
            resolves_in_hours=36,
            sport_key="politics",
        ),
    ]

    selected = selector.select(candidates, as_of=as_of)

    assert selected == []
