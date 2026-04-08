from datetime import UTC, date, datetime

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.domain.enums import PositionLifecycleState, SessionStatus
from pm_bot.domain.events import (
    PositionClosedEvent,
    PositionValuationUpdatedEvent,
    ProbeConfirmedEvent,
    ProbeOpenedEvent,
    ReconcileRecordedEvent,
    SessionOpenedEvent,
    SessionStoppedEvent,
    to_ledger_entry,
)
from pm_bot.storage.projector import LedgerProjector
from pm_bot.storage.schema import SCHEMA_VERSION, SNAPSHOT_VERSION


def test_projector_rebuilds_positions_sessions_and_snapshot() -> None:
    session_day = date(2026, 4, 8)
    opened_at = datetime(2026, 4, 8, 9, 0, tzinfo=UTC)
    closed_at = datetime(2026, 4, 8, 12, 0, tzinfo=UTC)

    entries = [
        to_ledger_entry(
            SessionOpenedEvent(
                session_date=session_day,
                status=SessionStatus.CAUTIOUS_START,
                updated_at=opened_at,
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            ProbeOpenedEvent(
                position_id="pos-1",
                market_id="mkt-1",
                market_title="Example Match",
                outcome_label="Team A",
                opened_at=opened_at,
                confirmation_deadline=datetime(2026, 4, 8, 13, 0, tzinfo=UTC),
                notional=20.0,
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            ProbeConfirmedEvent(
                position_id="pos-1",
                market_id="mkt-1",
                confirmed_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
                target_state=PositionLifecycleState.CONFIRMED_STAGE_1,
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            PositionValuationUpdatedEvent(
                position_id="pos-1",
                market_id="mkt-1",
                valued_at=datetime(2026, 4, 8, 11, 0, tzinfo=UTC),
                state=PositionLifecycleState.CONFIRMED_STAGE_1,
                exposure=20.0,
                unrealized_pnl=3.5,
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            ReconcileRecordedEvent(
                session_date=session_day,
                recorded_at=datetime(2026, 4, 8, 11, 30, tzinfo=UTC),
                summary="positions aligned",
                positions_in_sync=True,
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            PositionClosedEvent(
                position_id="pos-1",
                market_id="mkt-1",
                closed_at=closed_at,
                realized_pnl=8.0,
                close_reason="take_profit",
            ),
            schema_version=SCHEMA_VERSION,
        ),
        to_ledger_entry(
            SessionStoppedEvent(
                session_date=session_day,
                reason="two probe failures threshold reached",
                stopped_at=datetime(2026, 4, 8, 14, 0, tzinfo=UTC),
            ),
            schema_version=SCHEMA_VERSION,
        ),
    ]

    projector = LedgerProjector(
        runtime_mode=RuntimeMode.PAPER,
        validation_stage=ValidationStage.LOCAL_VALIDATION,
        starting_bankroll=1000.0,
        daily_loss_limit=75.0,
    )

    positions, sessions, risks, snapshot = projector.project(entries)

    assert len(positions) == 1
    assert positions[0].state is PositionLifecycleState.EXITED
    assert positions[0].realized_pnl == 8.0
    assert sessions[-1].status is SessionStatus.STOPPED_FOR_DAY
    assert risks[-1].open_risk == 0.0
    assert snapshot.total_capital == 1008.0
    assert snapshot.realized_pnl_today == 8.0
    assert snapshot.open_positions_count == 0
    assert snapshot.snapshot_version == SNAPSHOT_VERSION
