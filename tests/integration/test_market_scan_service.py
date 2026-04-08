from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.integrations.polymarket.gamma_client import GammaClient
from pm_bot.services.market_scan_service import MarketScanService


def test_market_scan_service_writes_paper_artifact(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "artifact_root": tmp_path / "artifacts",
            "candidate_window_hours": 72,
        }
    )
    service = MarketScanService(config, GammaClient("https://gamma-api.polymarket.com"))
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "gamma_markets" / "sample_markets.json"
    )

    selected, artifact_path = service.scan_fixture(fixture_path)

    assert len(selected) == 2
    assert artifact_path.exists()
