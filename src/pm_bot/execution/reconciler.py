from dataclasses import dataclass
from datetime import date, datetime

from pm_bot.domain.events import ReconcileRecordedEvent


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    summary: str
    positions_in_sync: bool


class PaperReconciler:
    def reconcile(
        self,
        *,
        session_date: date,
        observed_open_positions: int,
        recorded_open_positions: int,
        recorded_at: datetime,
    ) -> tuple[ReconcileResult, ReconcileRecordedEvent]:
        positions_in_sync = observed_open_positions == recorded_open_positions
        summary = (
            "paper positions aligned"
            if positions_in_sync
            else "paper positions diverged from in-memory state"
        )
        result = ReconcileResult(summary=summary, positions_in_sync=positions_in_sync)
        event = ReconcileRecordedEvent(
            session_date=session_date,
            recorded_at=recorded_at,
            summary=summary,
            positions_in_sync=positions_in_sync,
        )
        return result, event
