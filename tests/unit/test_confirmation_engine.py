from datetime import UTC, datetime

from pm_bot.domain.enums import PositionLifecycleState
from pm_bot.domain.models import MarketCandidate
from pm_bot.strategy.confirmation_engine import ConfirmationEngine
from pm_bot.strategy.reference_probability import EstimatedWinProbability


def _candidate() -> MarketCandidate:
    return MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 20, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.61,
        liquidity=120000.0,
    )


def _estimate(edge: float, *, tradeable: bool = True) -> EstimatedWinProbability:
    return EstimatedWinProbability(
        fair_probability=0.61 + edge,
        market_implied_probability=0.61,
        source_kind="fixture",
        source_timestamp=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        staleness_seconds=60,
        confidence_band=0.01,
        is_tradeable=tradeable,
        block_reason=None if tradeable else "reference_blocked",
        reference_event_id="ref-1",
        bookmaker_count=3,
    )


def test_confirmation_engine_confirms_probe_inside_window() -> None:
    engine = ConfirmationEngine(
        confirm_edge_threshold=0.05,
        add_stage_2_edge_threshold=0.06,
        exit_edge_threshold=0.01,
        min_hours_before_resolution=8,
        confirmation_window_hours=4,
    )

    decision = engine.decide(
        state=PositionLifecycleState.PROBE_LIVE,
        candidate=_candidate(),
        estimate=_estimate(0.06),
        opened_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        as_of=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
    )

    assert decision.action == "confirm_stage_1"


def test_confirmation_engine_exits_when_probe_expires() -> None:
    engine = ConfirmationEngine(
        confirm_edge_threshold=0.05,
        add_stage_2_edge_threshold=0.06,
        exit_edge_threshold=0.01,
        min_hours_before_resolution=8,
        confirmation_window_hours=4,
    )

    decision = engine.decide(
        state=PositionLifecycleState.PROBE_LIVE,
        candidate=_candidate(),
        estimate=_estimate(0.02),
        opened_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        as_of=datetime(2026, 4, 8, 14, 30, tzinfo=UTC),
    )

    assert decision.action == "exit"
    assert decision.reason == "confirmation_window_expired"
