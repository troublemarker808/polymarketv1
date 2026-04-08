from datetime import UTC, datetime

from pm_bot.config import AppConfig
from pm_bot.integrations.polymarket.gamma_client import GammaClient
from pm_bot.integrations.polymarket.models import GammaMarketDTO
from pm_bot.integrations.polymarket.translators import gamma_market_to_candidates
from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO
from pm_bot.integrations.reference_odds.the_odds_api_client import TheOddsApiClient
from pm_bot.services.trading_loop import PaperSessionResult, PaperTradingLoop
from pm_bot.strategy.event_identity_resolver import EventIdentityResolver


class PaperCanaryService:
    def __init__(
        self,
        config: AppConfig,
        *,
        gamma_client: GammaClient | None = None,
        reference_client: TheOddsApiClient | None = None,
    ) -> None:
        self._config = config
        self._gamma_client = gamma_client or GammaClient(config.polymarket_gamma_url)
        self._reference_client = reference_client or TheOddsApiClient(
            config.reference_odds_url,
            api_key=config.reference_odds_api_key,
        )
        self._resolver = EventIdentityResolver(
            match_window_minutes=config.event_match_window_minutes
        )
        self._trading_loop = PaperTradingLoop(config)

    def run_live_once(self) -> PaperSessionResult:
        as_of = datetime.now(tz=UTC)
        reference_events = self._reference_client.fetch_upcoming_h2h()
        sport_codes = _derive_gamma_sport_codes(reference_events)
        gamma_markets = self._gamma_client.fetch_sports_markets(
            sport_codes=sport_codes,
            events_limit_per_sport=self._config.gamma_scan_limit,
        )
        relevant_gamma_markets = [
            market
            for market in gamma_markets
            if _market_has_reference_match(market, reference_events, self._resolver)
        ]
        return self._trading_loop.run_snapshot_payload(
            timestamp=as_of,
            gamma_markets=[_serialize_gamma_market(item) for item in relevant_gamma_markets],
            reference_events=[
                _serialize_reference_event(item) for item in reference_events
            ],
        )


def _serialize_gamma_market(value: GammaMarketDTO) -> object:
    return {
        "id": value.market_id,
        "eventId": value.event_id,
        "question": value.question,
        "category": value.category,
        "active": value.active,
        "closed": value.closed,
        "liquidityNum": value.liquidity,
        "gameStartTime": value.starts_at.isoformat().replace("+00:00", "Z"),
        "endDate": value.resolves_at.isoformat().replace("+00:00", "Z"),
        "outcomes": list(value.outcomes),
        "outcomePrices": list(value.outcome_prices),
    }


def _serialize_reference_event(value: ReferenceOddsEventDTO) -> object:
    return {
        "id": value.event_id,
        "sport_key": value.sport_key,
        "commence_time": value.commence_time.isoformat().replace("+00:00", "Z"),
        "home_team": value.home_team,
        "away_team": value.away_team,
        "bookmakers": [
            {
                "key": bookmaker.key,
                "title": bookmaker.title,
                "markets": [
                    {
                        "key": market.key,
                        "last_update": market.last_update.isoformat().replace("+00:00", "Z"),
                        "outcomes": [
                            {"name": outcome.name, "price": outcome.price}
                            for outcome in market.outcomes
                        ],
                    }
                    for market in bookmaker.markets
                ],
            }
            for bookmaker in value.bookmakers
        ],
    }


def _derive_gamma_sport_codes(
    reference_events: list[ReferenceOddsEventDTO],
) -> set[str]:
    derived: set[str] = set()
    for event in reference_events:
        sport_key = event.sport_key.lower()
        if sport_key.startswith("soccer_epl"):
            derived.add("epl")
        elif sport_key.startswith("soccer_spain_la_liga"):
            derived.add("lal")
        elif sport_key.startswith("soccer_uefa_champs_league"):
            derived.add("ucl")
        elif sport_key.startswith("soccer_germany_bundesliga"):
            derived.add("bun")
        elif sport_key.startswith("basketball_nba"):
            derived.add("nba")
        elif sport_key.startswith("basketball_wnba"):
            derived.add("wnba")
        elif sport_key.startswith("baseball_mlb"):
            derived.add("mlb")
        elif sport_key.startswith("tennis_atp"):
            derived.add("atp")
        elif sport_key.startswith("tennis_wta"):
            derived.add("wta")
        elif sport_key == "cricket_odi":
            derived.add("odi")
        elif "t20" in sport_key:
            derived.add("t20")
    return derived


def _market_has_reference_match(
    market: GammaMarketDTO,
    reference_events: list[ReferenceOddsEventDTO],
    resolver: EventIdentityResolver,
) -> bool:
    return any(
        resolver.resolve(candidate, reference_events).resolved_event is not None
        for candidate in gamma_market_to_candidates(market)
    )
