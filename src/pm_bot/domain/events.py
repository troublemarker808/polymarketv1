from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import uuid4

from pm_bot.domain.enums import (
    AggregateType,
    LedgerEventType,
    PositionLifecycleState,
    SessionStatus,
)
from pm_bot.domain.models import LedgerEntry


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _parse_float(value: object) -> float:
    if isinstance(value, int | float | str):
        return float(value)
    msg = f"cannot parse float from value: {value!r}"
    raise TypeError(msg)


def _as_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


@dataclass(frozen=True, slots=True)
class SessionOpenedEvent:
    session_date: date
    status: SessionStatus
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class SessionStoppedEvent:
    session_date: date
    reason: str
    stopped_at: datetime


@dataclass(frozen=True, slots=True)
class ReconcileRecordedEvent:
    session_date: date
    recorded_at: datetime
    summary: str
    positions_in_sync: bool


@dataclass(frozen=True, slots=True)
class ProbeOpenedEvent:
    position_id: str
    market_id: str
    market_title: str
    outcome_label: str
    opened_at: datetime
    confirmation_deadline: datetime
    notional: float
    entry_price: float | None = None
    reference_event_id: str | None = None


@dataclass(frozen=True, slots=True)
class ProbeConfirmedEvent:
    position_id: str
    market_id: str
    confirmed_at: datetime
    target_state: PositionLifecycleState
    additional_notional: float | None = None
    confirmation_price: float | None = None


@dataclass(frozen=True, slots=True)
class PositionValuationUpdatedEvent:
    position_id: str
    market_id: str
    valued_at: datetime
    state: PositionLifecycleState
    exposure: float
    unrealized_pnl: float


@dataclass(frozen=True, slots=True)
class PositionClosedEvent:
    position_id: str
    market_id: str
    closed_at: datetime
    realized_pnl: float
    close_reason: str


@dataclass(frozen=True, slots=True)
class KillSwitchUpdatedEvent:
    session_date: date
    enabled: bool
    changed_at: datetime
    reason: str


DomainEvent = (
    SessionOpenedEvent
    | SessionStoppedEvent
    | ReconcileRecordedEvent
    | ProbeOpenedEvent
    | ProbeConfirmedEvent
    | PositionValuationUpdatedEvent
    | PositionClosedEvent
    | KillSwitchUpdatedEvent
)


def to_ledger_entry(event: DomainEvent, *, schema_version: int) -> LedgerEntry:
    if isinstance(event, SessionOpenedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.updated_at,
            event_type=LedgerEventType.SESSION_OPENED,
            aggregate_type=AggregateType.SESSION,
            aggregate_id=event.session_date.isoformat(),
            payload={
                "session_date": event.session_date.isoformat(),
                "status": event.status.value,
                "updated_at": _as_iso(event.updated_at),
            },
            schema_version=schema_version,
        )
    if isinstance(event, SessionStoppedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.stopped_at,
            event_type=LedgerEventType.SESSION_STOPPED,
            aggregate_type=AggregateType.SESSION,
            aggregate_id=event.session_date.isoformat(),
            payload={
                "session_date": event.session_date.isoformat(),
                "reason": event.reason,
                "stopped_at": _as_iso(event.stopped_at),
            },
            schema_version=schema_version,
        )
    if isinstance(event, ReconcileRecordedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.recorded_at,
            event_type=LedgerEventType.RECONCILE_RECORDED,
            aggregate_type=AggregateType.SESSION,
            aggregate_id=event.session_date.isoformat(),
            payload={
                "session_date": event.session_date.isoformat(),
                "recorded_at": _as_iso(event.recorded_at),
                "summary": event.summary,
                "positions_in_sync": event.positions_in_sync,
            },
            schema_version=schema_version,
        )
    if isinstance(event, ProbeOpenedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.opened_at,
            event_type=LedgerEventType.PROBE_OPENED,
            aggregate_type=AggregateType.POSITION,
            aggregate_id=event.position_id,
            payload={
                "position_id": event.position_id,
                "market_id": event.market_id,
                "market_title": event.market_title,
                "outcome_label": event.outcome_label,
                "opened_at": _as_iso(event.opened_at),
                "confirmation_deadline": _as_iso(event.confirmation_deadline),
                "notional": event.notional,
                "entry_price": event.entry_price,
                "reference_event_id": event.reference_event_id,
            },
            schema_version=schema_version,
        )
    if isinstance(event, ProbeConfirmedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.confirmed_at,
            event_type=LedgerEventType.PROBE_CONFIRMED,
            aggregate_type=AggregateType.POSITION,
            aggregate_id=event.position_id,
            payload={
                "position_id": event.position_id,
                "market_id": event.market_id,
                "confirmed_at": _as_iso(event.confirmed_at),
                "target_state": event.target_state.value,
                "additional_notional": event.additional_notional,
                "confirmation_price": event.confirmation_price,
            },
            schema_version=schema_version,
        )
    if isinstance(event, PositionValuationUpdatedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.valued_at,
            event_type=LedgerEventType.POSITION_VALUATION_UPDATED,
            aggregate_type=AggregateType.POSITION,
            aggregate_id=event.position_id,
            payload={
                "position_id": event.position_id,
                "market_id": event.market_id,
                "valued_at": _as_iso(event.valued_at),
                "state": event.state.value,
                "exposure": event.exposure,
                "unrealized_pnl": event.unrealized_pnl,
            },
            schema_version=schema_version,
        )
    if isinstance(event, PositionClosedEvent):
        return LedgerEntry(
            event_id=str(uuid4()),
            occurred_at=event.closed_at,
            event_type=LedgerEventType.POSITION_CLOSED,
            aggregate_type=AggregateType.POSITION,
            aggregate_id=event.position_id,
            payload={
                "position_id": event.position_id,
                "market_id": event.market_id,
                "closed_at": _as_iso(event.closed_at),
                "realized_pnl": event.realized_pnl,
                "close_reason": event.close_reason,
            },
            schema_version=schema_version,
        )

    return LedgerEntry(
        event_id=str(uuid4()),
        occurred_at=event.changed_at,
        event_type=LedgerEventType.KILL_SWITCH_UPDATED,
        aggregate_type=AggregateType.SYSTEM,
        aggregate_id=event.session_date.isoformat(),
        payload={
            "session_date": event.session_date.isoformat(),
            "enabled": event.enabled,
            "changed_at": _as_iso(event.changed_at),
            "reason": event.reason,
        },
        schema_version=schema_version,
    )


def decode_event(entry: LedgerEntry) -> DomainEvent:
    payload = entry.payload
    if entry.event_type is LedgerEventType.SESSION_OPENED:
        return SessionOpenedEvent(
            session_date=_parse_date(str(payload["session_date"])),
            status=SessionStatus(str(payload["status"])),
            updated_at=_parse_datetime(str(payload["updated_at"])),
        )
    if entry.event_type is LedgerEventType.SESSION_STOPPED:
        return SessionStoppedEvent(
            session_date=_parse_date(str(payload["session_date"])),
            reason=str(payload["reason"]),
            stopped_at=_parse_datetime(str(payload["stopped_at"])),
        )
    if entry.event_type is LedgerEventType.RECONCILE_RECORDED:
        return ReconcileRecordedEvent(
            session_date=_parse_date(str(payload["session_date"])),
            recorded_at=_parse_datetime(str(payload["recorded_at"])),
            summary=str(payload["summary"]),
            positions_in_sync=bool(payload["positions_in_sync"]),
        )
    if entry.event_type is LedgerEventType.PROBE_OPENED:
        reference_event_id = payload.get("reference_event_id")
        parsed_reference_event_id = (
            None if reference_event_id in (None, "None") else str(reference_event_id)
        )
        return ProbeOpenedEvent(
            position_id=str(payload["position_id"]),
            market_id=str(payload["market_id"]),
            market_title=str(payload["market_title"]),
            outcome_label=str(payload["outcome_label"]),
            opened_at=_parse_datetime(str(payload["opened_at"])),
            confirmation_deadline=_parse_datetime(str(payload["confirmation_deadline"])),
            notional=_parse_float(payload["notional"]),
            entry_price=_parse_float(payload["entry_price"])
            if payload.get("entry_price") is not None
            else None,
            reference_event_id=parsed_reference_event_id,
        )
    if entry.event_type is LedgerEventType.PROBE_CONFIRMED:
        return ProbeConfirmedEvent(
            position_id=str(payload["position_id"]),
            market_id=str(payload["market_id"]),
            confirmed_at=_parse_datetime(str(payload["confirmed_at"])),
            target_state=PositionLifecycleState(str(payload["target_state"])),
            additional_notional=_parse_float(payload["additional_notional"])
            if payload.get("additional_notional") is not None
            else None,
            confirmation_price=_parse_float(payload["confirmation_price"])
            if payload.get("confirmation_price") is not None
            else None,
        )
    if entry.event_type is LedgerEventType.POSITION_VALUATION_UPDATED:
        return PositionValuationUpdatedEvent(
            position_id=str(payload["position_id"]),
            market_id=str(payload["market_id"]),
            valued_at=_parse_datetime(str(payload["valued_at"])),
            state=PositionLifecycleState(str(payload["state"])),
            exposure=_parse_float(payload["exposure"]),
            unrealized_pnl=_parse_float(payload["unrealized_pnl"]),
        )
    if entry.event_type is LedgerEventType.POSITION_CLOSED:
        return PositionClosedEvent(
            position_id=str(payload["position_id"]),
            market_id=str(payload["market_id"]),
            closed_at=_parse_datetime(str(payload["closed_at"])),
            realized_pnl=_parse_float(payload["realized_pnl"]),
            close_reason=str(payload["close_reason"]),
        )

    return KillSwitchUpdatedEvent(
        session_date=_parse_date(str(payload["session_date"])),
        enabled=bool(payload["enabled"]),
        changed_at=_parse_datetime(str(payload["changed_at"])),
        reason=str(payload["reason"]),
    )
