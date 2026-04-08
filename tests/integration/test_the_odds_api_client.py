from pathlib import Path

import httpx

from pm_bot.integrations.reference_odds.the_odds_api_client import TheOddsApiClient


def test_the_odds_api_client_fetches_fixture_like_events() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "reference_odds"
        / "sample_events.json"
    )
    payload = fixture_path.read_text(encoding="utf-8")

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v4/sports/upcoming/odds"
        assert request.url.params["apiKey"] == "test-key"
        assert request.url.params["markets"] == "h2h"
        return httpx.Response(200, text=payload)

    transport = httpx.MockTransport(handler)
    client = TheOddsApiClient(
        "https://api.the-odds-api.com/v4",
        api_key="test-key",
        transport=transport,
    )

    events = client.fetch_upcoming_h2h()

    assert len(events) == 1
    assert events[0].event_id == "ref-1"
    assert events[0].home_team == "Team A"
