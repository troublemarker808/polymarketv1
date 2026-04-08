from datetime import UTC, date, datetime

from pm_bot.domain.enums import SessionStatus
from pm_bot.domain.models import DailyRiskState, MarketCandidate, SessionState
from pm_bot.strategy.probe_policy import ProbePolicy
from pm_bot.strategy.reference_probability import EstimatedWinProbability


def _candidate() -> MarketCandidate:
    return MarketCandidate(
        market_id="m1",
        event_id="e1",
        market_title="Will Team A beat Team B?",
        outcome_label="Team A",
        sport_key="sports",
        starts_at=datetime(2026, 4, 8, 18, 0, tzinfo=UTC),
        resolves_at=datetime(2026, 4, 9, 3, 0, tzinfo=UTC),
        market_implied_probability=0.61,
        liquidity=120000.0,
    )


def _estimate(edge: float, *, tradeable: bool = True) -> EstimatedWinProbability:
    return EstimatedWinProbability(
        fair_probability=0.61 + edge,
        market_implied_probability=0.61,
        source_kind="fixture",
        source_timestamp=datetime(2026, 4, 8, 8, 55, tzinfo=UTC),
        staleness_seconds=60,
        confidence_band=0.01,
        is_tradeable=tradeable,
        block_reason=None if tradeable else "reference_blocked",
        reference_event_id="ref-1",
        bookmaker_count=3,
    )


def test_probe_policy_opens_probe_when_edge_and_risk_allow() -> None:
    policy = ProbePolicy(
        probe_edge_threshold=0.04,
        confirm_window_hours=4,
        min_hours_before_resolution=8,
        probe_notional=20.0,
        daily_loss_limit=75.0,
        market_max_notional=60.0,
    )

    decision = policy.decide(
        _candidate(),
        _estimate(0.05),
        session_state=SessionState(
            session_date=date(2026, 4, 8),
            status=SessionStatus.RUNNING,
            stop_reason=None,
            cautious_until_probe_confirmed=False,
            consecutive_probe_failures=0,
            last_reconcile_at=None,
            last_stop_at=None,
            updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        ),
        daily_risk_state=DailyRiskState(
            session_date=date(2026, 4, 8),
            realized_loss=0.0,
            open_risk=0.0,
            daily_loss_limit=75.0,
            kill_switch_engaged=False,
            updated_at=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        ),
        current_market_exposure=0.0,
        as_of=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
    )

    assert decision.action == "probe"


def test_probe_policy_blocks_when_session_stopped() -> None:
    policy = ProbePolicy(
        probe_edge_threshold=0.04,
        confirm_window_hours=4,
        min_hours_before_resolution=8,
        probe_notional=20.0,
        daily_loss_limit=75.0,
        market_max_notional=60.0,
    )

    decision = policy.decide(
        _candidate(),
        _estimate(0.05),
        session_state=SessionState(
            session_date=date(2026, 4, 8),
            status=SessionStatus.STOPPED_FOR_DAY,
            stop_reason="two_probe_failures",
            cautious_until_probe_confirmed=False,
            consecutive_probe_failures=2,
            last_reconcile_at=None,
            last_stop_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
            updated_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
        ),
        daily_risk_state=DailyRiskState(
            session_date=date(2026, 4, 8),
            realized_loss=0.0,
            open_risk=0.0,
            daily_loss_limit=75.0,
            kill_switch_engaged=False,
            updated_at=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
        ),
        current_market_exposure=0.0,
        as_of=datetime(2026, 4, 8, 12, 0, tzinfo=UTC),
    )

    assert decision.action == "observe"
    assert decision.reason == "session_stopped_for_day"
