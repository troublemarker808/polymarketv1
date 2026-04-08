from dataclasses import dataclass
from datetime import datetime, timedelta

from pm_bot.domain.enums import PositionLifecycleState
from pm_bot.domain.models import MarketCandidate
from pm_bot.strategy.reference_probability import EstimatedWinProbability


@dataclass(frozen=True, slots=True)
class ConfirmationDecision:
    action: str
    reason: str
    target_state: PositionLifecycleState | None


class ConfirmationEngine:
    def __init__(
        self,
        *,
        confirm_edge_threshold: float,
        add_stage_2_edge_threshold: float,
        exit_edge_threshold: float,
        min_hours_before_resolution: int,
        confirmation_window_hours: int,
    ) -> None:
        self._confirm_edge_threshold = confirm_edge_threshold
        self._add_stage_2_edge_threshold = add_stage_2_edge_threshold
        self._exit_edge_threshold = exit_edge_threshold
        self._min_time_before_resolution = timedelta(hours=min_hours_before_resolution)
        self._confirmation_window = timedelta(hours=confirmation_window_hours)

    def decide(
        self,
        *,
        state: PositionLifecycleState,
        candidate: MarketCandidate,
        estimate: EstimatedWinProbability,
        opened_at: datetime,
        as_of: datetime,
    ) -> ConfirmationDecision:
        if state is PositionLifecycleState.PROBE_LIVE:
            if not estimate.is_tradeable:
                return ConfirmationDecision(
                    "exit",
                    estimate.block_reason or "reference_blocked",
                    None,
                )
            if as_of - opened_at > self._confirmation_window:
                return ConfirmationDecision("exit", "confirmation_window_expired", None)
            if candidate.starts_at - as_of < self._min_time_before_resolution:
                return ConfirmationDecision("exit", "too_close_to_resolution", None)
            if estimate.edge >= self._confirm_edge_threshold:
                return ConfirmationDecision(
                    "confirm_stage_1",
                    "edge_confirmed",
                    PositionLifecycleState.CONFIRMED_STAGE_1,
                )
            return ConfirmationDecision("hold", "awaiting_confirmation", None)

        if state is PositionLifecycleState.CONFIRMED_STAGE_1:
            if not estimate.is_tradeable or estimate.edge <= self._exit_edge_threshold:
                return ConfirmationDecision("exit", "edge_lost_after_stage_1", None)
            if estimate.edge >= self._add_stage_2_edge_threshold:
                return ConfirmationDecision(
                    "add_stage_2",
                    "edge_strong_enough_for_stage_2",
                    PositionLifecycleState.CONFIRMED_STAGE_2,
                )
            return ConfirmationDecision("hold", "holding_stage_1", None)

        if not estimate.is_tradeable or estimate.edge <= self._exit_edge_threshold:
            return ConfirmationDecision("exit", "edge_lost_after_stage_2", None)
        return ConfirmationDecision("hold", "holding_stage_2", None)
