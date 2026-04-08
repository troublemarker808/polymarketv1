from pathlib import Path

from fastapi.testclient import TestClient

from pm_bot.config import AppConfig
from pm_bot.services.local_validation import replay_fixture
from pm_bot.web.app import create_app


def test_dashboard_renders_projected_snapshot(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "state.sqlite3",
            "artifact_root": tmp_path / "artifacts",
        }
    )
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "local_validation"
        / "sample_session.json"
    )
    replay_fixture(config, fixture_path)

    response = TestClient(create_app(config)).get("/")

    assert response.status_code == 200
    assert "Polymarket Bot V3" in response.text
    assert "1008.00" in response.text
    assert "local_validation" in response.text
