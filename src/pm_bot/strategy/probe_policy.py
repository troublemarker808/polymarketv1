from dataclasses import dataclass
from datetime import datetime, timedelta

from pm_bot.domain.enums import SessionStatus
from pm_bot.domain.models import DailyRiskState, MarketCandidate, SessionState
from pm_bot.strategy.reference_probability import EstimatedWinProbability


@dataclass(frozen=True, slots=True)
class ProbeDecision:
    action: str
    reason: str
    probe_notional: float
    edge: float


class ProbePolicy:
    def __init__(
        self,
        *,
        probe_edge_threshold: float,
        confirm_window_hours: int,
        min_hours_before_resolution: int,
        probe_notional: float,
        daily_loss_limit: float,
        market_max_notional: float,
    ) -> None:
        self._probe_edge_threshold = probe_edge_threshold
        self._confirm_window = timedelta(hours=confirm_window_hours)
        self._min_time_before_resolution = timedelta(hours=min_hours_before_resolution)
        self._probe_notional = probe_notional
        self._daily_loss_limit = daily_loss_limit
        self._market_max_notional = market_max_notional

    def decide(
        self,
        candidate: MarketCandidate,
        estimate: EstimatedWinProbability,
        *,
        session_state: SessionState,
        daily_risk_state: DailyRiskState,
        current_market_exposure: float,
        as_of: datetime,
    ) -> ProbeDecision:
        if session_state.status is SessionStatus.STOPPED_FOR_DAY:
            return ProbeDecision("observe", "session_stopped_for_day", 0.0, estimate.edge)
        if not estimate.is_tradeable:
            return ProbeDecision(
                "observe",
                estimate.block_reason or "reference_blocked",
                0.0,
                estimate.edge,
            )
        if candidate.starts_at - as_of < self._min_time_before_resolution:
            return ProbeDecision("observe", "too_close_to_resolution", 0.0, estimate.edge)
        if daily_risk_state.realized_loss >= self._daily_loss_limit:
            return ProbeDecision("observe", "daily_loss_limit_reached", 0.0, estimate.edge)
        if current_market_exposure + self._probe_notional > self._market_max_notional:
            return ProbeDecision("observe", "market_exposure_limit_reached", 0.0, estimate.edge)
        if estimate.edge < self._probe_edge_threshold:
            return ProbeDecision("observe", "edge_below_probe_threshold", 0.0, estimate.edge)
        return ProbeDecision(
            "probe",
            "edge_above_probe_threshold",
            self._probe_notional,
            estimate.edge,
        )

    @property
    def confirmation_window(self) -> timedelta:
        return self._confirm_window
