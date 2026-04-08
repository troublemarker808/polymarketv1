from dataclasses import dataclass

from pm_bot.domain.models import DailyRiskState
from pm_bot.risk.kill_switch import KillSwitchState


@dataclass(frozen=True, slots=True)
class RiskDecision:
    allowed: bool
    reason: str | None


class RiskLimits:
    def __init__(
        self,
        *,
        probe_notional: float,
        market_max_notional: float,
        daily_loss_limit: float,
    ) -> None:
        self.probe_notional = probe_notional
        self.market_max_notional = market_max_notional
        self.daily_loss_limit = daily_loss_limit

    def allow_probe(
        self,
        *,
        daily_risk_state: DailyRiskState,
        current_market_exposure: float,
        kill_switch: KillSwitchState,
    ) -> RiskDecision:
        kill_switch_reason = kill_switch.block_reason()
        if kill_switch_reason is not None:
            return RiskDecision(False, kill_switch_reason)
        if daily_risk_state.realized_loss >= self.daily_loss_limit:
            return RiskDecision(False, "daily_loss_limit_reached")
        if current_market_exposure + self.probe_notional > self.market_max_notional:
            return RiskDecision(False, "market_exposure_limit_reached")
        return RiskDecision(True, None)
