from datetime import UTC, datetime, timedelta

import pytest

from pm_bot.domain.enums import PositionLifecycleState
from pm_bot.domain.models import MarketCandidate, ProbeAttempt, TradePosition


def test_market_candidate_rejects_invalid_probability() -> None:
    with pytest.raises(ValueError, match="probability"):
        MarketCandidate(
            market_id="m1",
            event_id="e1",
            market_title="Title",
            outcome_label="YES",
            sport_key="soccer",
            starts_at=datetime.now(tz=UTC),
            resolves_at=datetime.now(tz=UTC) + timedelta(hours=4),
            market_implied_probability=1.1,
            liquidity=1000,
        )


def test_probe_attempt_requires_positive_notional() -> None:
    with pytest.raises(ValueError, match="positive"):
        ProbeAttempt(
            position_id="p1",
            market_id="m1",
            outcome_label="YES",
            opened_at=datetime.now(tz=UTC),
            confirmation_deadline=datetime.now(tz=UTC) + timedelta(hours=1),
            notional=0.0,
            implied_probability=0.55,
        )


def test_trade_position_reports_open_state_correctly() -> None:
    now = datetime.now(tz=UTC)
    position = TradePosition(
        position_id="p1",
        market_id="m1",
        market_title="Title",
        outcome_label="YES",
        state=PositionLifecycleState.CONFIRMED_STAGE_1,
        exposure=10.0,
        realized_pnl=0.0,
        unrealized_pnl=1.0,
        opened_at=now,
        updated_at=now,
    )

    assert position.is_open() is True
