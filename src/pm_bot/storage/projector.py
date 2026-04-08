from dataclasses import replace
from datetime import UTC, date, datetime

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.domain.enums import PositionLifecycleState, SessionStatus
from pm_bot.domain.events import (
    KillSwitchUpdatedEvent,
    PositionClosedEvent,
    PositionValuationUpdatedEvent,
    ProbeConfirmedEvent,
    ProbeOpenedEvent,
    ReconcileRecordedEvent,
    SessionOpenedEvent,
    SessionStoppedEvent,
    decode_event,
)
from pm_bot.domain.models import (
    DailyRiskState,
    DashboardSnapshot,
    LedgerEntry,
    SessionState,
    TradePosition,
)
from pm_bot.storage.schema import SNAPSHOT_VERSION


class LedgerProjector:
    def __init__(
        self,
        *,
        runtime_mode: RuntimeMode,
        validation_stage: ValidationStage,
        starting_bankroll: float,
        daily_loss_limit: float,
    ) -> None:
        self.runtime_mode = runtime_mode
        self.validation_stage = validation_stage
        self.starting_bankroll = starting_bankroll
        self.daily_loss_limit = daily_loss_limit

    def project(
        self, entries: list[LedgerEntry]
    ) -> tuple[list[TradePosition], list[SessionState], list[DailyRiskState], DashboardSnapshot]:
        positions: dict[str, TradePosition] = {}
        sessions: dict[date, SessionState] = {}
        daily_risks: dict[date, DailyRiskState] = {}
        realized_closes: list[tuple[datetime, float]] = []
        last_reconcile_at: datetime | None = None
        last_stop_reason: str | None = None
        kill_switch_engaged = False
        last_timestamp: datetime | None = None

        for entry in entries:
            event = decode_event(entry)
            if last_timestamp is None or entry.occurred_at > last_timestamp:
                last_timestamp = entry.occurred_at

            if isinstance(event, SessionOpenedEvent):
                sessions[event.session_date] = SessionState(
                    session_date=event.session_date,
                    status=event.status,
                    stop_reason=None,
                    cautious_until_probe_confirmed=event.status is SessionStatus.CAUTIOUS_START,
                    consecutive_probe_failures=0,
                    last_reconcile_at=None,
                    last_stop_at=None,
                    updated_at=event.updated_at,
                )
                daily_risks.setdefault(
                    event.session_date,
                    DailyRiskState(
                        session_date=event.session_date,
                        realized_loss=0.0,
                        open_risk=0.0,
                        daily_loss_limit=self.daily_loss_limit,
                        kill_switch_engaged=False,
                        updated_at=event.updated_at,
                    ),
                )
                continue

            if isinstance(event, SessionStoppedEvent):
                current = sessions.get(event.session_date)
                base = current or SessionState(
                    session_date=event.session_date,
                    status=SessionStatus.RUNNING,
                    stop_reason=None,
                    cautious_until_probe_confirmed=False,
                    consecutive_probe_failures=0,
                    last_reconcile_at=None,
                    last_stop_at=None,
                    updated_at=event.stopped_at,
                )
                sessions[event.session_date] = replace(
                    base,
                    status=SessionStatus.STOPPED_FOR_DAY,
                    stop_reason=event.reason,
                    last_stop_at=event.stopped_at,
                    updated_at=event.stopped_at,
                )
                last_stop_reason = event.reason
                continue

            if isinstance(event, ReconcileRecordedEvent):
                current = sessions.get(event.session_date)
                base = current or SessionState(
                    session_date=event.session_date,
                    status=SessionStatus.RUNNING,
                    stop_reason=None,
                    cautious_until_probe_confirmed=False,
                    consecutive_probe_failures=0,
                    last_reconcile_at=None,
                    last_stop_at=None,
                    updated_at=event.recorded_at,
                )
                sessions[event.session_date] = replace(
                    base,
                    last_reconcile_at=event.recorded_at,
                    updated_at=event.recorded_at,
                )
                last_reconcile_at = event.recorded_at
                continue

            if isinstance(event, ProbeOpenedEvent):
                positions[event.position_id] = TradePosition(
                    position_id=event.position_id,
                    market_id=event.market_id,
                    market_title=event.market_title,
                    outcome_label=event.outcome_label,
                    state=PositionLifecycleState.PROBE_LIVE,
                    exposure=event.notional,
                    realized_pnl=0.0,
                    unrealized_pnl=0.0,
                    opened_at=event.opened_at,
                    updated_at=event.opened_at,
                    reference_event_id=event.reference_event_id,
                )
                self._set_open_risk(daily_risks, event.opened_at.date(), positions, event.opened_at)
                continue

            if isinstance(event, ProbeConfirmedEvent):
                existing = positions[event.position_id]
                positions[event.position_id] = replace(
                    existing,
                    state=event.target_state,
                    updated_at=event.confirmed_at,
                )
                session = sessions.get(event.confirmed_at.date())
                if session is not None and session.cautious_until_probe_confirmed:
                    sessions[event.confirmed_at.date()] = replace(
                        session,
                        status=SessionStatus.RUNNING,
                        cautious_until_probe_confirmed=False,
                        updated_at=event.confirmed_at,
                    )
                continue

            if isinstance(event, PositionValuationUpdatedEvent):
                existing = positions[event.position_id]
                positions[event.position_id] = replace(
                    existing,
                    state=event.state,
                    exposure=event.exposure,
                    unrealized_pnl=event.unrealized_pnl,
                    updated_at=event.valued_at,
                )
                self._set_open_risk(daily_risks, event.valued_at.date(), positions, event.valued_at)
                continue

            if isinstance(event, PositionClosedEvent):
                existing = positions[event.position_id]
                positions[event.position_id] = replace(
                    existing,
                    state=PositionLifecycleState.EXITED,
                    exposure=0.0,
                    unrealized_pnl=0.0,
                    realized_pnl=existing.realized_pnl + event.realized_pnl,
                    updated_at=event.closed_at,
                )
                realized_closes.append((event.closed_at, event.realized_pnl))
                self._record_realized_loss(
                    daily_risks=daily_risks,
                    session_date=event.closed_at.date(),
                    pnl=event.realized_pnl,
                    updated_at=event.closed_at,
                )
                self._set_open_risk(daily_risks, event.closed_at.date(), positions, event.closed_at)
                session = sessions.get(event.closed_at.date())
                if session is not None and event.close_reason == "unconfirmed":
                    sessions[event.closed_at.date()] = replace(
                        session,
                        consecutive_probe_failures=session.consecutive_probe_failures + 1,
                        updated_at=event.closed_at,
                    )
                continue

            assert isinstance(event, KillSwitchUpdatedEvent)
            kill_switch_engaged = event.enabled
            risk_current = daily_risks.get(event.session_date)
            risk_base = risk_current or DailyRiskState(
                session_date=event.session_date,
                realized_loss=0.0,
                open_risk=0.0,
                daily_loss_limit=self.daily_loss_limit,
                kill_switch_engaged=False,
                updated_at=event.changed_at,
            )
            daily_risks[event.session_date] = replace(
                risk_base,
                kill_switch_engaged=event.enabled,
                updated_at=event.changed_at,
            )

        snapshot = self._build_dashboard_snapshot(
            positions=positions,
            sessions=sessions,
            realized_closes=realized_closes,
            kill_switch_engaged=kill_switch_engaged,
            last_reconcile_at=last_reconcile_at,
            last_stop_reason=last_stop_reason,
            last_timestamp=last_timestamp,
        )
        return (
            list(positions.values()),
            sorted(sessions.values(), key=lambda item: item.session_date),
            sorted(daily_risks.values(), key=lambda item: item.session_date),
            snapshot,
        )

    def _set_open_risk(
        self,
        daily_risks: dict[date, DailyRiskState],
        session_date: date,
        positions: dict[str, TradePosition],
        updated_at: datetime,
    ) -> None:
        open_risk = sum(position.exposure for position in positions.values() if position.is_open())
        current = daily_risks.get(session_date)
        base = current or DailyRiskState(
            session_date=session_date,
            realized_loss=0.0,
            open_risk=0.0,
            daily_loss_limit=self.daily_loss_limit,
            kill_switch_engaged=False,
            updated_at=updated_at,
        )
        daily_risks[session_date] = replace(base, open_risk=open_risk, updated_at=updated_at)

    def _record_realized_loss(
        self,
        *,
        daily_risks: dict[date, DailyRiskState],
        session_date: date,
        pnl: float,
        updated_at: datetime,
    ) -> None:
        current = daily_risks.get(session_date)
        base = current or DailyRiskState(
            session_date=session_date,
            realized_loss=0.0,
            open_risk=0.0,
            daily_loss_limit=self.daily_loss_limit,
            kill_switch_engaged=False,
            updated_at=updated_at,
        )
        realized_loss = base.realized_loss + max(-pnl, 0.0)
        daily_risks[session_date] = replace(
            base,
            realized_loss=realized_loss,
            updated_at=updated_at,
        )

    def _build_dashboard_snapshot(
        self,
        *,
        positions: dict[str, TradePosition],
        sessions: dict[date, SessionState],
        realized_closes: list[tuple[datetime, float]],
        kill_switch_engaged: bool,
        last_reconcile_at: datetime | None,
        last_stop_reason: str | None,
        last_timestamp: datetime | None,
    ) -> DashboardSnapshot:
        latest_session = max(sessions.values(), key=lambda item: item.session_date, default=None)
        anchor = latest_session.updated_at if latest_session is not None else last_timestamp
        if anchor is None:
            anchor = datetime.now(tz=UTC)
        anchor_date = anchor.date()
        current_week = anchor_date.isocalendar()[:2]
        current_month = (anchor_date.year, anchor_date.month)

        realized_today = 0.0
        realized_week = 0.0
        realized_month = 0.0

        for closed_at, realized in realized_closes:
            if closed_at.date() == anchor_date:
                realized_today += realized
            if closed_at.date().isocalendar()[:2] == current_week:
                realized_week += realized
            if (closed_at.year, closed_at.month) == current_month:
                realized_month += realized

        open_positions = [position for position in positions.values() if position.is_open()]
        unrealized_total = sum(position.unrealized_pnl for position in open_positions)
        realized_total = sum(position.realized_pnl for position in positions.values())
        total_capital = self.starting_bankroll + realized_total + unrealized_total

        session_status = (
            latest_session.status if latest_session is not None else SessionStatus.RUNNING
        )

        return DashboardSnapshot(
            total_capital=total_capital,
            realized_pnl_today=realized_today,
            unrealized_pnl_today=unrealized_total,
            realized_pnl_week=realized_week,
            realized_pnl_month=realized_month,
            open_positions_count=len(open_positions),
            session_status=session_status,
            runtime_mode=self.runtime_mode,
            validation_stage=self.validation_stage,
            last_stop_reason=last_stop_reason if latest_session is not None else None,
            last_reconcile_at=last_reconcile_at,
            kill_switch_engaged=kill_switch_engaged,
            updated_at=anchor,
            snapshot_version=SNAPSHOT_VERSION,
        )
