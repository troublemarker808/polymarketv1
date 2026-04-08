from dataclasses import replace
from datetime import datetime

from pm_bot.domain.enums import SessionStatus
from pm_bot.domain.models import SessionState


class SessionGuard:
    def record_probe_failure(self, session_state: SessionState, *, at: datetime) -> SessionState:
        failures = session_state.consecutive_probe_failures + 1
        if failures >= 2:
            return replace(
                session_state,
                status=SessionStatus.STOPPED_FOR_DAY,
                stop_reason="two_probe_failures",
                consecutive_probe_failures=failures,
                last_stop_at=at,
                updated_at=at,
            )
        return replace(
            session_state,
            consecutive_probe_failures=failures,
            updated_at=at,
        )

    def record_probe_confirmation(
        self,
        session_state: SessionState,
        *,
        at: datetime,
    ) -> SessionState:
        return replace(
            session_state,
            status=SessionStatus.RUNNING,
            cautious_until_probe_confirmed=False,
            updated_at=at,
        )
