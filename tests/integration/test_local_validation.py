import json
from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.services.local_validation import replay_fixture
from pm_bot.storage.db import connect_database
from pm_bot.storage.repositories import ProjectionRepository


def test_replay_fixture_generates_artifact_and_snapshot(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "state.sqlite3",
            "artifact_root": tmp_path / "artifacts",
            "initial_bankroll": 1000.0,
            "daily_loss_notional": 75.0,
        }
    )

    fixture_path = tmp_path / "fixture.json"
    fixture_payload = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "local_validation"
        / "sample_session.json"
    )
    fixture_path.write_text(fixture_payload.read_text(encoding="utf-8"), encoding="utf-8")

    artifact_path = replay_fixture(config, fixture_path)

    assert artifact_path.exists()
    payload = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert payload["snapshot"]["total_capital"] == 1008.0

    connection = connect_database(config.database_path)
    snapshot = ProjectionRepository(connection).fetch_dashboard_snapshot()
    assert snapshot is not None
    assert snapshot.total_capital == 1008.0
