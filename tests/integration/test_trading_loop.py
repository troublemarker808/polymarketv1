import json
from datetime import UTC, datetime
from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.services.trading_loop import PaperTradingLoop
from pm_bot.storage.db import connect_database
from pm_bot.storage.repositories import ProjectionRepository


def test_paper_trading_loop_generates_session_artifacts(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "state.sqlite3",
            "artifact_root": tmp_path / "artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "paper_sessions"
        / "healthy_session.json"
    )

    result = PaperTradingLoop(config).run_fixture(fixture_path)

    assert result.processed_snapshots == 4
    assert result.stopped_for_day is False
    assert result.session_summary_path.exists()
    assert result.probe_log_path.exists()
    assert result.incident_note_path is None

    snapshot = ProjectionRepository(
        connect_database(config.database_path)
    ).fetch_dashboard_snapshot()
    assert snapshot is not None
    assert snapshot.total_capital > 1000.0


def test_paper_trading_loop_stops_after_two_unconfirmed_probes(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "stop-state.sqlite3",
            "artifact_root": tmp_path / "stop-artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "paper_sessions"
        / "stop_after_two_failures.json"
    )

    result = PaperTradingLoop(config).run_fixture(fixture_path)

    assert result.stopped_for_day is True
    assert result.incident_note_path is None


def test_paper_trading_loop_recovers_open_positions_across_runs(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "resume-state.sqlite3",
            "artifact_root": tmp_path / "resume-artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    source_fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "paper_sessions"
        / "healthy_session.json"
    )
    payload = json.loads(source_fixture.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    assert isinstance(payload["snapshots"], list)

    first_run_fixture = tmp_path / "first-run.json"
    second_run_fixture = tmp_path / "second-run.json"
    first_run_fixture.write_text(
        json.dumps({"snapshots": payload["snapshots"][:2]}),
        encoding="utf-8",
    )
    second_run_fixture.write_text(
        json.dumps({"snapshots": payload["snapshots"][2:]}),
        encoding="utf-8",
    )

    first_result = PaperTradingLoop(config).run_fixture(first_run_fixture)
    assert first_result.stopped_for_day is False
    assert first_result.incident_note_path is None
    assert ProjectionRepository(connect_database(config.database_path)).fetch_open_positions()

    second_result = PaperTradingLoop(config).run_fixture(second_run_fixture)

    assert second_result.processed_snapshots == 2
    snapshot = ProjectionRepository(
        connect_database(config.database_path)
    ).fetch_dashboard_snapshot()
    assert snapshot is not None
    assert snapshot.total_capital > 1000.0


def test_paper_trading_loop_writes_incident_when_live_run_has_only_observes(
    tmp_path: Path,
) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "incident-state.sqlite3",
            "artifact_root": tmp_path / "incident-artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )

    result = PaperTradingLoop(config).run_snapshot_payload(
        timestamp=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        gamma_markets=[
            {
                "id": "m-live-incident",
                "eventId": "e-live-incident",
                "question": "Will Team X beat Team Y?",
                "category": "Sports",
                "active": True,
                "closed": False,
                "liquidityNum": 80000,
                "gameStartTime": "2026-04-08T20:00:00Z",
                "endDate": "2026-04-09T03:00:00Z",
                "outcomes": ["Team X", "Team Y"],
                "outcomePrices": [0.57, 0.43],
            }
        ],
        reference_events=[],
    )

    assert result.incident_note_path is not None
    assert result.incident_note_path.exists()
