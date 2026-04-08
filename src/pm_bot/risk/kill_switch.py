from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KillSwitchState:
    engaged: bool
    reason: str | None = None

    def block_reason(self) -> str | None:
        if self.engaged:
            return self.reason or "kill_switch_engaged"
        return None
