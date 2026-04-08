from pm_bot.app_modes import RuntimeMode, ValidationStage
from pm_bot.config import AppConfig
from pm_bot.services.promotion_gate import PaperGateDecision, evaluate_paper_gate


def require_small_live_prerequisites(config: AppConfig) -> PaperGateDecision:
    if config.runtime_mode is not RuntimeMode.LIVE_SMALL:
        msg = "small_live guard can only validate the live_small runtime mode"
        raise RuntimeError(msg)
    if config.validation_stage is not ValidationStage.SMALL_LIVE_VALIDATION:
        msg = "small_live requires validation_stage=small_live_validation"
        raise RuntimeError(msg)

    decision = evaluate_paper_gate(config)
    if not decision.ready_for_small_live_validation:
        reasons = ", ".join(decision.reasons)
        msg = f"small_live blocked by paper gate: {reasons}"
        raise RuntimeError(msg)
    return decision
