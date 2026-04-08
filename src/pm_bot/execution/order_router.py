from datetime import datetime
from uuid import uuid4

from pm_bot.domain.enums import PositionLifecycleState
from pm_bot.domain.events import (
    PositionClosedEvent,
    PositionValuationUpdatedEvent,
    ProbeConfirmedEvent,
    ProbeOpenedEvent,
)
from pm_bot.execution.position_service import (
    PaperPosition,
    add_to_position,
    mark_to_market,
    open_position,
    realize_close,
)


class PaperOrderRouter:
    def open_probe(
        self,
        *,
        market_id: str,
        market_title: str,
        outcome_label: str,
        price: float,
        notional: float,
        opened_at: datetime,
        confirmation_deadline: datetime,
        reference_event_id: str | None,
    ) -> tuple[PaperPosition, ProbeOpenedEvent]:
        position_id = str(uuid4())
        position = open_position(
            position_id=position_id,
            market_id=market_id,
            market_title=market_title,
            outcome_label=outcome_label,
            price=price,
            notional=notional,
            opened_at=opened_at,
            reference_event_id=reference_event_id,
        )
        event = ProbeOpenedEvent(
            position_id=position.position_id,
            market_id=market_id,
            market_title=market_title,
            outcome_label=outcome_label,
            opened_at=opened_at,
            confirmation_deadline=confirmation_deadline,
            notional=notional,
            entry_price=price,
            reference_event_id=reference_event_id,
        )
        return position, event

    def confirm_stage(
        self,
        position: PaperPosition,
        *,
        additional_notional: float,
        price: float,
        target_state: PositionLifecycleState,
        confirmed_at: datetime,
    ) -> tuple[PaperPosition, ProbeConfirmedEvent, PositionValuationUpdatedEvent]:
        updated_position = add_to_position(
            position,
            additional_notional=additional_notional,
            price=price,
            next_state=target_state,
            updated_at=confirmed_at,
        )
        valuation = mark_to_market(updated_position, price=price)
        return (
            updated_position,
            ProbeConfirmedEvent(
                position_id=position.position_id,
                market_id=position.market_id,
                confirmed_at=confirmed_at,
                target_state=target_state,
                additional_notional=additional_notional,
                confirmation_price=price,
            ),
            PositionValuationUpdatedEvent(
                position_id=position.position_id,
                market_id=position.market_id,
                valued_at=confirmed_at,
                state=target_state,
                exposure=updated_position.notional,
                unrealized_pnl=valuation,
            ),
        )

    def value_position(
        self,
        position: PaperPosition,
        *,
        price: float,
        valued_at: datetime,
    ) -> PositionValuationUpdatedEvent:
        valuation = mark_to_market(position, price=price)
        return PositionValuationUpdatedEvent(
            position_id=position.position_id,
            market_id=position.market_id,
            valued_at=valued_at,
            state=position.state,
            exposure=position.notional,
            unrealized_pnl=valuation,
        )

    def close_position(
        self,
        position: PaperPosition,
        *,
        price: float,
        reason: str,
        closed_at: datetime,
    ) -> PositionClosedEvent:
        realized = realize_close(position, price=price)
        return PositionClosedEvent(
            position_id=position.position_id,
            market_id=position.market_id,
            closed_at=closed_at,
            realized_pnl=realized,
            close_reason=reason,
        )
