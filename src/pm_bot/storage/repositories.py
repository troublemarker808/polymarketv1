import json
import sqlite3
from collections.abc import Sequence
from datetime import date, datetime
from typing import cast

from pm_bot.domain.enums import (
    AggregateType,
    LedgerEventType,
    PositionLifecycleState,
    SessionStatus,
)
from pm_bot.domain.models import (
    DailyRiskState,
    DashboardSnapshot,
    LedgerEntry,
    SessionState,
    TradePosition,
)


def _as_optional_iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _parse_optional_datetime(value: object) -> datetime | None:
    if value in (None, ""):
        return None
    return datetime.fromisoformat(str(value))


class LedgerRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def append(self, entry: LedgerEntry) -> None:
        self.connection.execute(
            """
            INSERT INTO ledger_entries(
                event_id,
                occurred_at,
                event_type,
                aggregate_type,
                aggregate_id,
                payload_json,
                schema_version
            ) VALUES(?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.event_id,
                entry.occurred_at.isoformat(),
                entry.event_type.value,
                entry.aggregate_type.value,
                entry.aggregate_id,
                json.dumps(entry.payload),
                entry.schema_version,
            ),
        )
        self.connection.commit()

    def list_all(self) -> list[LedgerEntry]:
        rows = self.connection.execute(
            """
            SELECT
                event_id,
                occurred_at,
                event_type,
                aggregate_type,
                aggregate_id,
                payload_json,
                schema_version
            FROM ledger_entries
            ORDER BY id ASC
            """
        ).fetchall()
        entries: list[LedgerEntry] = []
        for row in rows:
            entries.append(
                LedgerEntry(
                    event_id=str(row["event_id"]),
                    occurred_at=datetime.fromisoformat(str(row["occurred_at"])),
                    event_type=LedgerEventType(str(row["event_type"])),
                    aggregate_type=AggregateType(str(row["aggregate_type"])),
                    aggregate_id=str(row["aggregate_id"]),
                    payload=cast(dict[str, object], json.loads(str(row["payload_json"]))),
                    schema_version=int(row["schema_version"]),
                )
            )
        return entries


class ProjectionRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def clear(self) -> None:
        self.connection.execute("DELETE FROM positions")
        self.connection.execute("DELETE FROM session_state")
        self.connection.execute("DELETE FROM daily_risk_state")
        self.connection.execute("DELETE FROM dashboard_snapshot")
        self.connection.commit()

    def replace_positions(self, positions: Sequence[TradePosition], *, last_event_id: str) -> None:
        self.connection.execute("DELETE FROM positions")
        for position in positions:
            self.connection.execute(
                """
                INSERT INTO positions(
                    position_id,
                    market_id,
                    market_title,
                    outcome_label,
                    state,
                    exposure,
                    realized_pnl,
                    unrealized_pnl,
                    opened_at,
                    updated_at,
                    reference_event_id,
                    last_event_id
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    position.position_id,
                    position.market_id,
                    position.market_title,
                    position.outcome_label,
                    position.state.value,
                    position.exposure,
                    position.realized_pnl,
                    position.unrealized_pnl,
                    position.opened_at.isoformat(),
                    position.updated_at.isoformat(),
                    position.reference_event_id,
                    last_event_id,
                ),
            )
        self.connection.commit()

    def replace_session_states(self, sessions: Sequence[SessionState]) -> None:
        self.connection.execute("DELETE FROM session_state")
        for session in sessions:
            self.connection.execute(
                """
                INSERT INTO session_state(
                    session_date, status, stop_reason, cautious_until_probe_confirmed,
                    consecutive_probe_failures, last_reconcile_at, last_stop_at, updated_at
                ) VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.session_date.isoformat(),
                    session.status.value,
                    session.stop_reason,
                    int(session.cautious_until_probe_confirmed),
                    session.consecutive_probe_failures,
                    _as_optional_iso(session.last_reconcile_at),
                    _as_optional_iso(session.last_stop_at),
                    session.updated_at.isoformat(),
                ),
            )
        self.connection.commit()

    def replace_daily_risk_states(self, states: Sequence[DailyRiskState]) -> None:
        self.connection.execute("DELETE FROM daily_risk_state")
        for state in states:
            self.connection.execute(
                """
                INSERT INTO daily_risk_state(
                    session_date,
                    realized_loss,
                    open_risk,
                    daily_loss_limit,
                    kill_switch_engaged,
                    updated_at
                ) VALUES(?, ?, ?, ?, ?, ?)
                """,
                (
                    state.session_date.isoformat(),
                    state.realized_loss,
                    state.open_risk,
                    state.daily_loss_limit,
                    int(state.kill_switch_engaged),
                    state.updated_at.isoformat(),
                ),
            )
        self.connection.commit()

    def replace_dashboard_snapshot(self, snapshot: DashboardSnapshot) -> None:
        self.connection.execute("DELETE FROM dashboard_snapshot")
        self.connection.execute(
            """
            INSERT INTO dashboard_snapshot(
                snapshot_id,
                total_capital,
                realized_pnl_today,
                unrealized_pnl_today,
                realized_pnl_week,
                realized_pnl_month,
                open_positions_count,
                session_status,
                runtime_mode,
                validation_stage,
                last_stop_reason,
                last_reconcile_at,
                kill_switch_engaged,
                updated_at,
                snapshot_version
            ) VALUES(1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                snapshot.total_capital,
                snapshot.realized_pnl_today,
                snapshot.unrealized_pnl_today,
                snapshot.realized_pnl_week,
                snapshot.realized_pnl_month,
                snapshot.open_positions_count,
                snapshot.session_status.value,
                snapshot.runtime_mode.value,
                snapshot.validation_stage.value,
                snapshot.last_stop_reason,
                _as_optional_iso(snapshot.last_reconcile_at),
                int(snapshot.kill_switch_engaged),
                snapshot.updated_at.isoformat(),
                snapshot.snapshot_version,
            ),
        )
        self.connection.commit()

    def fetch_dashboard_snapshot(self) -> DashboardSnapshot | None:
        row = self.connection.execute(
            "SELECT * FROM dashboard_snapshot WHERE snapshot_id = 1"
        ).fetchone()
        if row is None:
            return None

        from pm_bot.app_modes import RuntimeMode, ValidationStage

        last_stop_reason = None if row["last_stop_reason"] is None else str(row["last_stop_reason"])
        return DashboardSnapshot(
            total_capital=float(row["total_capital"]),
            realized_pnl_today=float(row["realized_pnl_today"]),
            unrealized_pnl_today=float(row["unrealized_pnl_today"]),
            realized_pnl_week=float(row["realized_pnl_week"]),
            realized_pnl_month=float(row["realized_pnl_month"]),
            open_positions_count=int(row["open_positions_count"]),
            session_status=SessionStatus(str(row["session_status"])),
            runtime_mode=RuntimeMode(str(row["runtime_mode"])),
            validation_stage=ValidationStage(str(row["validation_stage"])),
            last_stop_reason=last_stop_reason,
            last_reconcile_at=_parse_optional_datetime(row["last_reconcile_at"]),
            kill_switch_engaged=bool(row["kill_switch_engaged"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
            snapshot_version=int(row["snapshot_version"]),
        )

    def fetch_open_positions(self) -> list[TradePosition]:
        rows = self.connection.execute(
            "SELECT * FROM positions WHERE state != 'exited' AND exposure > 0 ORDER BY opened_at"
        ).fetchall()
        positions: list[TradePosition] = []
        for row in rows:
            positions.append(
                TradePosition(
                    position_id=str(row["position_id"]),
                    market_id=str(row["market_id"]),
                    market_title=str(row["market_title"]),
                    outcome_label=str(row["outcome_label"]),
                    state=PositionLifecycleState(str(row["state"])),
                    exposure=float(row["exposure"]),
                    realized_pnl=float(row["realized_pnl"]),
                    unrealized_pnl=float(row["unrealized_pnl"]),
                    opened_at=datetime.fromisoformat(str(row["opened_at"])),
                    updated_at=datetime.fromisoformat(str(row["updated_at"])),
                    reference_event_id=None
                    if row["reference_event_id"] is None
                    else str(row["reference_event_id"]),
                )
            )
        return positions

    def fetch_session_state(self, session_date: date) -> SessionState | None:
        row = self.connection.execute(
            "SELECT * FROM session_state WHERE session_date = ?",
            (session_date.isoformat(),),
        ).fetchone()
        if row is None:
            return None
        return SessionState(
            session_date=date.fromisoformat(str(row["session_date"])),
            status=SessionStatus(str(row["status"])),
            stop_reason=None if row["stop_reason"] is None else str(row["stop_reason"]),
            cautious_until_probe_confirmed=bool(row["cautious_until_probe_confirmed"]),
            consecutive_probe_failures=int(row["consecutive_probe_failures"]),
            last_reconcile_at=_parse_optional_datetime(row["last_reconcile_at"]),
            last_stop_at=_parse_optional_datetime(row["last_stop_at"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def fetch_latest_session_state(self) -> SessionState | None:
        row = self.connection.execute(
            "SELECT * FROM session_state ORDER BY session_date DESC LIMIT 1"
        ).fetchone()
        if row is None:
            return None
        return SessionState(
            session_date=date.fromisoformat(str(row["session_date"])),
            status=SessionStatus(str(row["status"])),
            stop_reason=None if row["stop_reason"] is None else str(row["stop_reason"]),
            cautious_until_probe_confirmed=bool(row["cautious_until_probe_confirmed"]),
            consecutive_probe_failures=int(row["consecutive_probe_failures"]),
            last_reconcile_at=_parse_optional_datetime(row["last_reconcile_at"]),
            last_stop_at=_parse_optional_datetime(row["last_stop_at"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )

    def fetch_daily_risk_state(self, session_date: date) -> DailyRiskState | None:
        row = self.connection.execute(
            "SELECT * FROM daily_risk_state WHERE session_date = ?",
            (session_date.isoformat(),),
        ).fetchone()
        if row is None:
            return None
        return DailyRiskState(
            session_date=date.fromisoformat(str(row["session_date"])),
            realized_loss=float(row["realized_loss"]),
            open_risk=float(row["open_risk"]),
            daily_loss_limit=float(row["daily_loss_limit"]),
            kill_switch_engaged=bool(row["kill_switch_engaged"]),
            updated_at=datetime.fromisoformat(str(row["updated_at"])),
        )
