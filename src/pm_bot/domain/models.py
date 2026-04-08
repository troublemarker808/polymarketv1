from dataclasses import dataclass
from datetime import date, datetime

from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.domain.enums import (
    AggregateType,
    LedgerEventType,
    PositionLifecycleState,
    SessionStatus,
)


def _ensure_probability(value: float) -> None:
    if not 0.0 <= value <= 1.0:
        msg = "probability values must be within [0, 1]"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class MarketCandidate:
    market_id: str
    event_id: str
    market_title: str
    outcome_label: str
    sport_key: str
    starts_at: datetime
    resolves_at: datetime
    market_implied_probability: float
    liquidity: float
    observe_only_reason: str | None = None

    def __post_init__(self) -> None:
        _ensure_probability(self.market_implied_probability)
        if self.liquidity < 0:
            msg = "liquidity must be non-negative"
            raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class ProbeAttempt:
    position_id: str
    market_id: str
    outcome_label: str
    opened_at: datetime
    confirmation_deadline: datetime
    notional: float
    implied_probability: float
    reference_event_id: str | None = None

    def __post_init__(self) -> None:
        if self.notional <= 0:
            msg = "probe notional must be positive"
            raise ValueError(msg)
        _ensure_probability(self.implied_probability)


@dataclass(frozen=True, slots=True)
class TradePosition:
    position_id: str
    market_id: str
    market_title: str
    outcome_label: str
    state: PositionLifecycleState
    exposure: float
    realized_pnl: float
    unrealized_pnl: float
    opened_at: datetime
    updated_at: datetime
    reference_event_id: str | None = None

    def is_open(self) -> bool:
        return self.state is not PositionLifecycleState.EXITED and self.exposure > 0


@dataclass(frozen=True, slots=True)
class SessionState:
    session_date: date
    status: SessionStatus
    stop_reason: str | None
    cautious_until_probe_confirmed: bool
    consecutive_probe_failures: int
    last_reconcile_at: datetime | None
    last_stop_at: datetime | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DailyRiskState:
    session_date: date
    realized_loss: float
    open_risk: float
    daily_loss_limit: float
    kill_switch_engaged: bool
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardSnapshot:
    total_capital: float
    realized_pnl_today: float
    unrealized_pnl_today: float
    realized_pnl_week: float
    realized_pnl_month: float
    open_positions_count: int
    session_status: SessionStatus
    runtime_mode: RuntimeMode
    validation_stage: ValidationStage
    last_stop_reason: str | None
    last_reconcile_at: datetime | None
    kill_switch_engaged: bool
    updated_at: datetime
    snapshot_version: int


@dataclass(frozen=True, slots=True)
class LedgerEntry:
    event_id: str
    occurred_at: datetime
    event_type: LedgerEventType
    aggregate_type: AggregateType
    aggregate_id: str
    payload: dict[str, object]
    schema_version: int
