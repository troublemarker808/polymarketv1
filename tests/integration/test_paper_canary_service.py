from datetime import UTC, datetime
from pathlib import Path

from pm_bot.config import AppConfig
from pm_bot.integrations.polymarket.gamma_client import GammaClient
from pm_bot.integrations.polymarket.models import GammaMarketDTO
from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO
from pm_bot.integrations.reference_odds.the_odds_api_client import TheOddsApiClient
from pm_bot.services.paper_canary import PaperCanaryService
from pm_bot.storage.db import connect_database
from pm_bot.storage.repositories import ProjectionRepository


class _StubGammaClient(GammaClient):
    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    def fetch_markets(self, *, limit: int) -> list[GammaMarketDTO]:
        del limit
        return super().load_fixture(self._fixture_path)

    def fetch_sports_markets(
        self,
        *,
        sport_codes: set[str],
        events_limit_per_sport: int = 20,
    ) -> list[GammaMarketDTO]:
        del sport_codes, events_limit_per_sport
        return super().load_fixture(self._fixture_path)


class _StubReferenceClient(TheOddsApiClient):
    def __init__(self, fixture_path: Path) -> None:
        self._fixture_path = fixture_path

    def fetch_upcoming_h2h(self) -> list[ReferenceOddsEventDTO]:
        return super().load_fixture(self._fixture_path)


def test_paper_canary_service_runs_live_once_with_read_only_sources(tmp_path: Path) -> None:
    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "state.sqlite3",
            "artifact_root": tmp_path / "artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    gamma_fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "gamma_markets"
        / "sample_markets.json"
    )
    reference_fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "reference_odds"
        / "sample_events.json"
    )

    service = PaperCanaryService(
        config,
        gamma_client=_StubGammaClient(gamma_fixture),
        reference_client=_StubReferenceClient(reference_fixture),
    )

    result = service.run_live_once()

    assert result.processed_snapshots == 1
    assert result.session_summary_path.exists()
    snapshot = ProjectionRepository(
        connect_database(config.database_path)
    ).fetch_dashboard_snapshot()
    assert snapshot is not None
    assert snapshot.validation_stage.value == "paper_canary"


def test_paper_canary_service_uses_reference_sport_codes_for_gamma_fetch(tmp_path: Path) -> None:
    class _RecordingGammaClient(GammaClient):
        def __init__(self) -> None:
            self.requested_codes: set[str] | None = None

        def fetch_sports_markets(
            self,
            *,
            sport_codes: set[str],
            events_limit_per_sport: int = 20,
        ) -> list[GammaMarketDTO]:
            del events_limit_per_sport
            self.requested_codes = set(sport_codes)
            return []

    class _StubReference(TheOddsApiClient):
        def fetch_upcoming_h2h(self) -> list[ReferenceOddsEventDTO]:
            fixture_path = (
                Path(__file__).resolve().parents[1]
                / "fixtures"
                / "reference_odds"
                / "sample_events.json"
            )
            return super().load_fixture(fixture_path)

    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "state.sqlite3",
            "artifact_root": tmp_path / "artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    gamma_client = _RecordingGammaClient()
    service = PaperCanaryService(
        config,
        gamma_client=gamma_client,
        reference_client=_StubReference("unused", api_key="unused"),
    )

    service.run_live_once()

    assert gamma_client.requested_codes == {"epl"}


def test_paper_canary_service_filters_live_markets_to_reference_matches(
    tmp_path: Path,
) -> None:
    class _GammaWithMixedMarkets(GammaClient):
        def fetch_sports_markets(
            self,
            *,
            sport_codes: set[str],
            events_limit_per_sport: int = 20,
        ) -> list[GammaMarketDTO]:
            del sport_codes, events_limit_per_sport
            return [
                GammaMarketDTO(
                    market_id="match-1",
                    event_id="event-1",
                    question="Jiri Lehecka vs Alejandro Tabilo",
                    category="sports",
                    active=True,
                    closed=False,
                    liquidity=10000.0,
                    starts_at=reference_event.commence_time,
                    resolves_at=reference_event.commence_time,
                    outcomes=("Lehecka", "Tabilo"),
                    outcome_prices=(0.51, 0.49),
                ),
                GammaMarketDTO(
                    market_id="noise-1",
                    event_id="noise-event-1",
                    question="Will unrelated team win?",
                    category="sports",
                    active=True,
                    closed=False,
                    liquidity=10000.0,
                    starts_at=reference_event.commence_time,
                    resolves_at=reference_event.commence_time,
                    outcomes=("Yes", "No"),
                    outcome_prices=(0.51, 0.49),
                ),
            ]

    reference_event = ReferenceOddsEventDTO(
        event_id="ref-atp",
        sport_key="tennis_atp_monte_carlo_masters",
        commence_time=datetime(2026, 4, 8, 9, 0, tzinfo=UTC),
        home_team="Jiri Lehecka",
        away_team="Alejandro Tabilo",
        bookmakers=(),
    )

    class _ReferenceStub(TheOddsApiClient):
        def fetch_upcoming_h2h(self) -> list[ReferenceOddsEventDTO]:
            return [reference_event]

    config = AppConfig.from_mapping(
        {
            "database_path": tmp_path / "filter-state.sqlite3",
            "artifact_root": tmp_path / "filter-artifacts",
            "validation_stage": "paper_canary",
            "runtime_mode": "paper",
        }
    )
    service = PaperCanaryService(
        config,
        gamma_client=_GammaWithMixedMarkets("unused"),
        reference_client=_ReferenceStub("unused", api_key="unused"),
    )

    result = service.run_live_once()

    assert result.incident_note_path is not None
