from dataclasses import replace
from datetime import datetime, timedelta

from pm_bot.domain.models import MarketCandidate

DEFAULT_OBSERVE_ONLY_REASON = "reference_probability_unavailable"


class MarketSelector:
    def __init__(self, *, candidate_window_hours: int) -> None:
        self._candidate_window = timedelta(hours=candidate_window_hours)

    def select(
        self,
        candidates: list[MarketCandidate],
        *,
        as_of: datetime,
    ) -> list[MarketCandidate]:
        selected: list[MarketCandidate] = []
        for candidate in candidates:
            if not self._is_sports_candidate(candidate):
                continue
            if candidate.starts_at <= as_of:
                continue
            if candidate.starts_at - as_of > self._candidate_window:
                continue
            selected.append(
                replace(
                    candidate,
                    observe_only_reason=DEFAULT_OBSERVE_ONLY_REASON,
                )
            )
        return selected

    def _is_sports_candidate(self, candidate: MarketCandidate) -> bool:
        sport_key = candidate.sport_key.lower()
        if sport_key not in {"sports", "sport"}:
            return False

        normalized_outcome = candidate.outcome_label.strip().lower()
        return normalized_outcome not in {"draw", "tie"}
