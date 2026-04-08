from enum import StrEnum


class ValidationStage(StrEnum):
    ARCHITECTURE = "architecture"
    LOCAL_VALIDATION = "local_validation"
    PAPER_CANARY = "paper_canary"
    SMALL_LIVE_VALIDATION = "small_live_validation"


class RuntimeMode(StrEnum):
    PAPER = "paper"
    LIVE_SMALL = "live_small"


def is_pre_live_stage(stage: ValidationStage) -> bool:
    return stage in {
        ValidationStage.ARCHITECTURE,
        ValidationStage.LOCAL_VALIDATION,
        ValidationStage.PAPER_CANARY,
    }
