import json
from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.services.promotion_gate import evaluate_paper_gate


def test_promotion_gate_fails_when_evidence_is_insufficient(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "artifact_root": tmp_path / "artifacts",
            "promotion_min_paper_sessions": 3,
            "promotion_min_resolved_probes": 2,
        }
    )
    paper_dir = config.artifact_paths.paper
    paper_dir.mkdir(parents=True, exist_ok=True)

    _write_artifact(
        paper_dir,
        "daily-session-summary-20260408T120000Z.json",
        {
            "session_date": "2026-04-08",
            "evidence_source": "fixture_paper",
            "realized_loss": 0.0,
        },
    )
    _write_artifact(
        paper_dir,
        "probe-outcome-log-20260408T120000Z.json",
        {
            "session_date": "2026-04-08",
            "evidence_source": "fixture_paper",
            "probes": [{"position_id": "pos-1", "result": "probe_confirmed"}],
        },
    )

    decision = evaluate_paper_gate(config)

    assert decision.ready_for_small_live_validation is False
    assert "paper_artifacts_incomplete" in decision.reasons
    assert "promotion_eligible_session_count_below_minimum" in decision.reasons
    assert decision.engineering_blockers == [
        "paper_artifacts_incomplete",
        "weekly_pnl_snapshot_missing",
        "monthly_pnl_snapshot_missing",
    ]
    assert decision.evidence_gaps == [
        "promotion_eligible_session_count_below_minimum",
        "promotion_eligible_resolved_probe_count_below_minimum",
    ]
    assert decision.artifact_path.exists()


def test_promotion_gate_passes_with_complete_positive_evidence(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "artifact_root": tmp_path / "artifacts",
            "promotion_min_paper_sessions": 2,
            "promotion_min_resolved_probes": 2,
        }
    )
    paper_dir = config.artifact_paths.paper
    paper_dir.mkdir(parents=True, exist_ok=True)

    _write_complete_session(
        paper_dir,
        session_date="2026-04-08",
        timestamp="20260408T120000Z",
        realized_loss=1.5,
        weekly_pnl=4.0,
        monthly_pnl=4.0,
        probes=[
            {"position_id": "pos-1", "result": "probe_confirmed"},
            {"position_id": "pos-2", "result": "position_closed"},
        ],
        stopped_for_day=False,
    )
    _write_complete_session(
        paper_dir,
        session_date="2026-04-09",
        timestamp="20260409T120000Z",
        realized_loss=0.5,
        weekly_pnl=6.0,
        monthly_pnl=6.0,
        probes=[
            {"position_id": "pos-3", "result": "probe_confirmed"},
            {"position_id": "pos-4", "result": "position_closed"},
        ],
        stopped_for_day=False,
    )

    decision = evaluate_paper_gate(config)

    assert decision.ready_for_small_live_validation is True
    assert decision.reasons == []
    assert decision.engineering_blockers == []
    assert decision.evidence_gaps == []
    assert decision.metrics.complete_session_count == 2
    assert decision.metrics.resolved_probe_count == 4
    assert decision.metrics.remaining_sessions_to_minimum == 0
    assert decision.metrics.remaining_resolved_probes_to_minimum == 0


def _write_complete_session(
    paper_dir: Path,
    *,
    session_date: str,
    timestamp: str,
    realized_loss: float,
    weekly_pnl: float,
    monthly_pnl: float,
    probes: list[dict[str, object]],
    stopped_for_day: bool,
) -> None:
    _write_artifact(
        paper_dir,
        f"daily-session-summary-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "realized_loss": realized_loss,
        },
    )
    _write_artifact(
        paper_dir,
        f"probe-outcome-log-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "probes": probes,
        },
    )
    _write_artifact(
        paper_dir,
        f"stop-reason-summary-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "stopped_for_day": stopped_for_day,
            "stop_reason": None,
        },
    )
    _write_artifact(
        paper_dir,
        f"weekly-pnl-snapshot-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "realized_pnl_week": weekly_pnl,
            "realized_pnl_month": monthly_pnl,
        },
    )


def _write_artifact(directory: Path, name: str, payload: dict[str, object]) -> None:
    target = directory / name
    target.write_text(json.dumps(payload), encoding="utf-8")
