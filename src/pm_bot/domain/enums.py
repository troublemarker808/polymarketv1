from enum import StrEnum


class AggregateType(StrEnum):
    POSITION = "position"
    SESSION = "session"
    SYSTEM = "system"


class PositionLifecycleState(StrEnum):
    WATCHING = "watching"
    PROBE_PENDING = "probe_pending"
    PROBE_LIVE = "probe_live"
    CONFIRMED_STAGE_1 = "confirmed_stage_1"
    CONFIRMED_STAGE_2 = "confirmed_stage_2"
    EXITED = "exited"


class SessionStatus(StrEnum):
    RUNNING = "running"
    STOPPED_FOR_DAY = "stopped_for_day"
    CAUTIOUS_START = "cautious_start"


class LedgerEventType(StrEnum):
    SESSION_OPENED = "session_opened"
    SESSION_STOPPED = "session_stopped"
    RECONCILE_RECORDED = "reconcile_recorded"
    PROBE_OPENED = "probe_opened"
    PROBE_CONFIRMED = "probe_confirmed"
    POSITION_VALUATION_UPDATED = "position_valuation_updated"
    POSITION_CLOSED = "position_closed"
    KILL_SWITCH_UPDATED = "kill_switch_updated"
