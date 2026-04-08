from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.domain.models import MarketCandidate
from pm_bot.integrations.polymarket.gamma_client import GammaClient
from pm_bot.integrations.polymarket.models import GammaMarketDTO
from pm_bot.integrations.polymarket.translators import flatten_candidates
from pm_bot.services.artifacts import ensure_artifact_directories, write_json_artifact
from pm_bot.strategy.market_selector import MarketSelector


class MarketScanService:
    def __init__(self, config: AppConfig, gamma_client: GammaClient) -> None:
        self._config = config
        self._gamma_client = gamma_client
        self._selector = MarketSelector(candidate_window_hours=config.candidate_window_hours)

    def scan_live_gamma(self) -> tuple[list[MarketCandidate], Path]:
        markets = self._gamma_client.fetch_markets(limit=self._config.gamma_scan_limit)
        return self._finalize_scan(markets)

    def scan_fixture(self, fixture_path: Path) -> tuple[list[MarketCandidate], Path]:
        markets = self._gamma_client.load_fixture(fixture_path)
        return self._finalize_scan(markets)

    def _finalize_scan(
        self,
        markets: Sequence[GammaMarketDTO],
    ) -> tuple[list[MarketCandidate], Path]:
        as_of = datetime.now(tz=UTC)
        candidates = flatten_candidates(markets)
        selected = self._selector.select(candidates, as_of=as_of)
        ensure_artifact_directories(self._config.artifact_paths)
        artifact_path = write_json_artifact(
            self._config.artifact_paths.paper,
            prefix="paper-candidate-scan",
            payload={
                "as_of": as_of,
                "market_count": len(markets),
                "candidate_count": len(candidates),
                "selected_count": len(selected),
                "selected_candidates": selected,
            },
        )
        return selected, artifact_path
