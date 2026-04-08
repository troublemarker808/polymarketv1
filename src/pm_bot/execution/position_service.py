from dataclasses import dataclass, replace
from datetime import datetime

from pm_bot.domain.enums import PositionLifecycleState
from pm_bot.domain.events import (
    PositionClosedEvent,
    ProbeConfirmedEvent,
    ProbeOpenedEvent,
)
from pm_bot.domain.models import LedgerEntry


@dataclass(frozen=True, slots=True)
class PaperPosition:
    position_id: str
    market_id: str
    market_title: str
    outcome_label: str
    state: PositionLifecycleState
    notional: float
    average_price: float
    shares: float
    opened_at: datetime
    updated_at: datetime
    reference_event_id: str | None = None

    @property
    def exposure(self) -> float:
        return self.shares * self.average_price


def open_position(
    *,
    position_id: str,
    market_id: str,
    market_title: str,
    outcome_label: str,
    price: float,
    notional: float,
    opened_at: datetime,
    reference_event_id: str | None,
) -> PaperPosition:
    shares = notional / price
    return PaperPosition(
        position_id=position_id,
        market_id=market_id,
        market_title=market_title,
        outcome_label=outcome_label,
        state=PositionLifecycleState.PROBE_LIVE,
        notional=notional,
        average_price=price,
        shares=shares,
        opened_at=opened_at,
        updated_at=opened_at,
        reference_event_id=reference_event_id,
    )


def add_to_position(
    position: PaperPosition,
    *,
    additional_notional: float,
    price: float,
    next_state: PositionLifecycleState,
    updated_at: datetime,
) -> PaperPosition:
    additional_shares = additional_notional / price
    total_shares = position.shares + additional_shares
    total_notional = position.notional + additional_notional
    average_price = total_notional / total_shares
    return replace(
        position,
        state=next_state,
        notional=total_notional,
        average_price=average_price,
        shares=total_shares,
        updated_at=updated_at,
    )


def mark_to_market(position: PaperPosition, *, price: float) -> float:
    return position.shares * price - position.notional


def realize_close(position: PaperPosition, *, price: float) -> float:
    return mark_to_market(position, price=price)


def rebuild_open_positions(entries: list[LedgerEntry]) -> dict[str, PaperPosition]:
    from pm_bot.domain.events import decode_event

    positions: dict[str, PaperPosition] = {}
    for entry in entries:
        event = decode_event(entry)
        if isinstance(event, ProbeOpenedEvent):
            if event.entry_price is None:
                continue
            positions[event.position_id] = open_position(
                position_id=event.position_id,
                market_id=event.market_id,
                market_title=event.market_title,
                outcome_label=event.outcome_label,
                price=event.entry_price,
                notional=event.notional,
                opened_at=event.opened_at,
                reference_event_id=event.reference_event_id,
            )
            continue
        if isinstance(event, ProbeConfirmedEvent):
            position = positions.get(event.position_id)
            if (
                position is None
                or event.additional_notional is None
                or event.confirmation_price is None
            ):
                continue
            positions[event.position_id] = add_to_position(
                position,
                additional_notional=event.additional_notional,
                price=event.confirmation_price,
                next_state=event.target_state,
                updated_at=event.confirmed_at,
            )
            continue
        if isinstance(event, PositionClosedEvent):
            positions.pop(event.position_id, None)
    return positions
