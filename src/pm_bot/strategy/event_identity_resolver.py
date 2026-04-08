from dataclasses import dataclass
from datetime import datetime, timedelta

from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO

MATCH_RULE_VERSION = "v1"


@dataclass(frozen=True, slots=True)
class ResolvedReferenceEvent:
    reference_event_id: str
    matched_home: str
    matched_away: str
    matched_start_time: datetime
    match_rule_version: str


@dataclass(frozen=True, slots=True)
class EventMatchResult:
    resolved_event: ResolvedReferenceEvent | None
    block_reason: str | None


class EventIdentityResolver:
    def __init__(self, *, match_window_minutes: int) -> None:
        self._match_window = timedelta(minutes=match_window_minutes)

    def resolve(
        self,
        candidate: MarketCandidate,
        reference_events: list[ReferenceOddsEventDTO],
    ) -> EventMatchResult:
        matches = [event for event in reference_events if self._matches_candidate(candidate, event)]
        if not matches:
            return EventMatchResult(resolved_event=None, block_reason="reference_event_unmatched")
        if len(matches) > 1:
            return EventMatchResult(resolved_event=None, block_reason="reference_event_ambiguous")

        event = matches[0]
        return EventMatchResult(
            resolved_event=ResolvedReferenceEvent(
                reference_event_id=event.event_id,
                matched_home=event.home_team,
                matched_away=event.away_team,
                matched_start_time=event.commence_time,
                match_rule_version=MATCH_RULE_VERSION,
            ),
            block_reason=None,
        )

    def _matches_candidate(
        self,
        candidate: MarketCandidate,
        event: ReferenceOddsEventDTO,
    ) -> bool:
        event_names = (event.home_team, event.away_team)
        if not any(_matches_participant(candidate.outcome_label, name) for name in event_names):
            return False

        candidate_title = _normalize_name(candidate.market_title)
        if not all(
            _normalize_name(name) in candidate_title
            for name in (event.home_team, event.away_team)
        ):
            return False

        time_delta = abs(candidate.starts_at - event.commence_time)
        return time_delta <= self._match_window


def _normalize_name(value: str) -> str:
    return "".join(ch.lower() for ch in value if ch.isalnum())


def _matches_participant(candidate_value: str, event_name: str) -> bool:
    normalized_candidate = _normalize_name(candidate_value)
    normalized_event = _normalize_name(event_name)
    if normalized_candidate == normalized_event:
        return True

    event_parts = [part for part in event_name.lower().split() if part]
    if not event_parts:
        return False
    normalized_last_part = _normalize_name(event_parts[-1])
    return normalized_candidate == normalized_last_part
