from datetime import UTC, date, datetime

from pm_bot.domain.enums import SessionStatus
from pm_bot.domain.models import SessionState
from pm_bot.strategy.session_guard import SessionGuard


def test_session_guard_stops_after_two_probe_failures() -> None:
    guard = SessionGuard()
    state = SessionState(
        session_date=date(2026, 4, 8),
        status=SessionStatus.RUNNING,
        stop_reason=None,
        cautious_until_probe_confirmed=False,
        consecutive_probe_failures=1,
        last_reconcile_at=None,
        last_stop_at=None,
        updated_at=datetime(2026, 4, 8, 10, 0, tzinfo=UTC),
    )

    updated = guard.record_probe_failure(
        state,
        at=datetime(2026, 4, 8, 11, 0, tzinfo=UTC),
    )

    assert updated.status is SessionStatus.STOPPED_FOR_DAY
    assert updated.stop_reason == "two_probe_failures"
