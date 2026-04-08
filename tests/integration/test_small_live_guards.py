import json
from pathlib import Path

import pytest

from pm_bot.config import AppConfig
from pm_bot.services.small_live_guard import require_small_live_prerequisites


def test_small_live_guard_blocks_when_paper_gate_fails(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "artifact_root": tmp_path / "artifacts",
            "runtime_mode": "live_small",
            "validation_stage": "small_live_validation",
            "enable_live_small": True,
            "polymarket_private_key": "test-private",
            "polymarket_api_key": "test-key",
            "polymarket_api_secret": "test-secret",
            "polymarket_api_passphrase": "test-passphrase",
            "polymarket_funder": "test-funder",
        }
    )

    with pytest.raises(RuntimeError, match="small_live blocked by paper gate"):
        require_small_live_prerequisites(config)


def test_small_live_guard_passes_when_paper_gate_is_satisfied(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "artifact_root": tmp_path / "artifacts",
            "runtime_mode": "live_small",
            "validation_stage": "small_live_validation",
            "enable_live_small": True,
            "polymarket_private_key": "test-private",
            "polymarket_api_key": "test-key",
            "polymarket_api_secret": "test-secret",
            "polymarket_api_passphrase": "test-passphrase",
            "polymarket_funder": "test-funder",
            "promotion_min_paper_sessions": 2,
            "promotion_min_resolved_probes": 2,
        }
    )
    paper_dir = config.artifact_paths.paper
    paper_dir.mkdir(parents=True, exist_ok=True)
    _write_complete_session(paper_dir, "2026-04-08", "20260408T120000Z")
    _write_complete_session(paper_dir, "2026-04-09", "20260409T120000Z")

    decision = require_small_live_prerequisites(config)

    assert decision.ready_for_small_live_validation is True


def _write_complete_session(paper_dir: Path, session_date: str, timestamp: str) -> None:
    _write_artifact(
        paper_dir / f"daily-session-summary-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "realized_loss": 1.0,
        },
    )
    _write_artifact(
        paper_dir / f"probe-outcome-log-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "probes": [
                {"position_id": f"{session_date}-1", "result": "probe_confirmed"},
                {"position_id": f"{session_date}-2", "result": "position_closed"},
            ],
        },
    )
    _write_artifact(
        paper_dir / f"stop-reason-summary-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "stopped_for_day": False,
            "stop_reason": None,
        },
    )
    _write_artifact(
        paper_dir / f"weekly-pnl-snapshot-{timestamp}.json",
        {
            "session_date": session_date,
            "evidence_source": "read_only_live_paper",
            "realized_pnl_week": 5.0,
            "realized_pnl_month": 5.0,
        },
    )


def _write_artifact(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")
