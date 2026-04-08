import json
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from pm_bot.config import AppConfig
from pm_bot.services.artifacts import write_json_artifact

REQUIRED_PAPER_ARTIFACTS = (
    "daily-session-summary",
    "probe-outcome-log",
    "stop-reason-summary",
    "weekly-pnl-snapshot",
)
PROMOTION_ELIGIBLE_EVIDENCE_SOURCES = {"read_only_live_paper"}


@dataclass(frozen=True, slots=True)
class PaperGateMetrics:
    complete_session_count: int
    promotion_eligible_session_count: int
    fixture_session_count: int
    missing_artifact_session_dates: list[str]
    resolved_probe_count: int
    promotion_eligible_resolved_probe_count: int
    successful_probe_count: int
    stopped_session_count: int
    latest_realized_pnl_week: float | None
    latest_realized_pnl_month: float | None
    max_realized_loss: float
    remaining_sessions_to_minimum: int
    remaining_resolved_probes_to_minimum: int


@dataclass(frozen=True, slots=True)
class PaperGateDecision:
    ready_for_small_live_validation: bool
    reasons: list[str]
    engineering_blockers: list[str]
    evidence_gaps: list[str]
    metrics: PaperGateMetrics
    artifact_path: Path


def evaluate_paper_gate(config: AppConfig) -> PaperGateDecision:
    paper_dir = config.artifact_paths.paper
    artifacts_by_session = _load_paper_artifacts(paper_dir)
    resolved_position_ids: set[str] = set()
    successful_position_ids: set[str] = set()

    complete_sessions = 0
    promotion_eligible_sessions = 0
    fixture_sessions = 0
    missing_sessions: list[str] = []
    resolved_probe_count = 0
    promotion_eligible_resolved_probe_count = 0
    successful_probe_count = 0
    stopped_session_count = 0
    latest_week_pnl: float | None = None
    latest_month_pnl: float | None = None
    max_realized_loss = 0.0

    for session_date, artifact_map in sorted(artifacts_by_session.items()):
        missing_prefixes = [
            prefix for prefix in REQUIRED_PAPER_ARTIFACTS if prefix not in artifact_map
        ]
        if missing_prefixes:
            missing_sessions.append(session_date.isoformat())
            continue

        complete_sessions += 1
        session_summary = artifact_map["daily-session-summary"]
        stop_summary = artifact_map["stop-reason-summary"]
        weekly_snapshot = artifact_map["weekly-pnl-snapshot"]
        evidence_source = str(session_summary.get("evidence_source", "fixture_paper"))
        if evidence_source in PROMOTION_ELIGIBLE_EVIDENCE_SOURCES:
            promotion_eligible_sessions += 1
        else:
            fixture_sessions += 1

        realized_loss = _as_float(session_summary.get("realized_loss"), default=0.0)
        max_realized_loss = max(max_realized_loss, realized_loss or 0.0)

        if bool(stop_summary.get("stopped_for_day")):
            stopped_session_count += 1

        latest_week_pnl = _as_float(
            weekly_snapshot.get("realized_pnl_week"),
            default=latest_week_pnl,
        )
        latest_month_pnl = _as_float(
            weekly_snapshot.get("realized_pnl_month"),
            default=latest_month_pnl,
        )

    for artifact_path in sorted(paper_dir.glob("probe-outcome-log-*.json")):
        payload = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        evidence_source = str(payload.get("evidence_source", "fixture_paper"))
        for item in _as_list(payload.get("probes")):
            if not isinstance(item, dict) or "position_id" not in item:
                continue
            position_id = str(item["position_id"])
            if item.get("result") in {"probe_confirmed", "position_closed"}:
                resolved_position_ids.add(position_id)
                if evidence_source in PROMOTION_ELIGIBLE_EVIDENCE_SOURCES:
                    promotion_eligible_resolved_probe_count += 1
            if item.get("result") == "probe_confirmed":
                successful_position_ids.add(position_id)

    resolved_probe_count = len(resolved_position_ids)
    successful_probe_count = len(successful_position_ids)

    metrics = PaperGateMetrics(
        complete_session_count=complete_sessions,
        promotion_eligible_session_count=promotion_eligible_sessions,
        fixture_session_count=fixture_sessions,
        missing_artifact_session_dates=missing_sessions,
        resolved_probe_count=resolved_probe_count,
        promotion_eligible_resolved_probe_count=promotion_eligible_resolved_probe_count,
        successful_probe_count=successful_probe_count,
        stopped_session_count=stopped_session_count,
        latest_realized_pnl_week=latest_week_pnl,
        latest_realized_pnl_month=latest_month_pnl,
        max_realized_loss=max_realized_loss,
        remaining_sessions_to_minimum=max(
            config.promotion_min_paper_sessions - promotion_eligible_sessions,
            0,
        ),
        remaining_resolved_probes_to_minimum=max(
            config.promotion_min_resolved_probes - promotion_eligible_resolved_probe_count,
            0,
        ),
    )
    engineering_blockers, evidence_gaps = _evaluate_reasons(config, metrics)
    reasons = engineering_blockers + evidence_gaps
    artifact_path = write_json_artifact(
        config.artifact_paths.promotion,
        prefix="paper-gate-decision",
        payload={
            "ready_for_small_live_validation": not reasons,
            "reasons": reasons,
            "engineering_blockers": engineering_blockers,
            "evidence_gaps": evidence_gaps,
            "metrics": metrics,
            "required_artifacts": list(REQUIRED_PAPER_ARTIFACTS),
            "evaluated_at": datetime.now(tz=UTC),
            "current_stage": config.validation_stage.value,
            "next_stage_candidate": "small_live_validation",
        },
    )
    return PaperGateDecision(
        ready_for_small_live_validation=not reasons,
        reasons=reasons,
        engineering_blockers=engineering_blockers,
        evidence_gaps=evidence_gaps,
        metrics=metrics,
        artifact_path=artifact_path,
    )


def _evaluate_reasons(
    config: AppConfig,
    metrics: PaperGateMetrics,
) -> tuple[list[str], list[str]]:
    engineering_blockers: list[str] = []
    evidence_gaps: list[str] = []
    if metrics.missing_artifact_session_dates:
        engineering_blockers.append("paper_artifacts_incomplete")
    if metrics.promotion_eligible_session_count < config.promotion_min_paper_sessions:
        evidence_gaps.append("promotion_eligible_session_count_below_minimum")
    if (
        metrics.promotion_eligible_resolved_probe_count
        < config.promotion_min_resolved_probes
    ):
        evidence_gaps.append("promotion_eligible_resolved_probe_count_below_minimum")
    if metrics.latest_realized_pnl_week is None:
        engineering_blockers.append("weekly_pnl_snapshot_missing")
    elif metrics.latest_realized_pnl_week < 0:
        evidence_gaps.append("weekly_pnl_negative")
    if metrics.latest_realized_pnl_month is None:
        engineering_blockers.append("monthly_pnl_snapshot_missing")
    elif metrics.latest_realized_pnl_month < 0:
        evidence_gaps.append("monthly_pnl_negative")

    daily_loss_limit = min(
        config.initial_bankroll * config.daily_loss_fraction,
        config.daily_loss_notional,
    )
    if metrics.max_realized_loss > daily_loss_limit:
        evidence_gaps.append("daily_loss_limit_breached_in_paper")
    return engineering_blockers, evidence_gaps


def _load_paper_artifacts(paper_dir: Path) -> dict[date, dict[str, dict[str, Any]]]:
    by_session: dict[date, dict[str, dict[str, Any]]] = {}
    for prefix in REQUIRED_PAPER_ARTIFACTS:
        for artifact_path in sorted(paper_dir.glob(f"{prefix}-*.json")):
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            if not isinstance(payload, dict):
                continue
            session_value = payload.get("session_date")
            if not isinstance(session_value, str):
                continue
            session_date = date.fromisoformat(session_value)
            session_entry = by_session.setdefault(session_date, {})
            session_entry[prefix] = payload
    return by_session


def _as_list(value: object) -> list[object]:
    if isinstance(value, list):
        return value
    return []


def _as_float(value: object, *, default: float | None) -> float | None:
    if value is None:
        return default
    if isinstance(value, int | float | str):
        return float(value)
    return default
