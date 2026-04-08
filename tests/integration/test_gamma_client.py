from pathlib import Path

import httpx

from pm_bot.integrations.polymarket.gamma_client import GammaClient


def test_gamma_client_fetches_and_parses_markets_from_http_fixture() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1] / "fixtures" / "gamma_markets" / "sample_markets.json"
    )
    payload = fixture_path.read_text(encoding="utf-8")

    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=payload))
    client = GammaClient("https://gamma-api.polymarket.com", transport=transport)

    markets = client.fetch_markets(limit=10)

    assert len(markets) == 3
    assert markets[0].market_id == "m-100"
    assert markets[0].outcome_prices == (0.61, 0.39)


def test_gamma_client_parses_stringified_outcome_arrays() -> None:
    payload = """
    [
      {
        "id": "m-live-1",
        "eventId": "e-live-1",
        "question": "Will Team A beat Team B?",
        "category": "Sports",
        "active": true,
        "closed": false,
        "liquidityNum": "10000",
        "startDate": "2026-04-08T09:00:00Z",
        "endDate": "2026-04-09T03:00:00Z",
        "outcomes": "[\\"Team A\\", \\"Team B\\"]",
        "outcomePrices": "[0.58, 0.42]"
      }
    ]
    """
    transport = httpx.MockTransport(lambda request: httpx.Response(200, text=payload))
    client = GammaClient("https://gamma-api.polymarket.com", transport=transport)

    markets = client.fetch_markets(limit=10)

    assert len(markets) == 1
    assert markets[0].outcomes == ("Team A", "Team B")
    assert markets[0].outcome_prices == (0.58, 0.42)


def test_gamma_client_fetches_sports_markets_via_sports_and_events_endpoints() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sports":
            return httpx.Response(
                200,
                json=[
                    {"sport": "epl", "tags": "1,82,306"},
                    {"sport": "mlb", "tags": "1,100381"},
                ],
            )
        if request.url.path == "/events":
            tag_id = request.url.params.get("tag_id")
            if tag_id == "82":
                return httpx.Response(
                    200,
                    json=[
                        {
                            "id": "event-1",
                            "title": "West Ham United FC vs. Wolverhampton Wanderers FC",
                            "startDate": "2026-04-10T19:00:00Z",
                            "endDate": "2026-04-10T21:00:00Z",
                            "markets": [
                                {
                                    "id": "market-1",
                                    "question": "Spread: West Ham United FC (-1.5)",
                                    "active": True,
                                    "closed": False,
                                    "liquidityNum": "11000",
                                    "gameStartTime": "2026-04-10T19:00:00Z",
                                    "endDate": "2026-04-10T21:00:00Z",
                                    "outcomes": (
                                        "[\"West Ham United FC\", "
                                        "\"Wolverhampton Wanderers FC\"]"
                                    ),
                                    "outcomePrices": "[0.48, 0.52]",
                                }
                            ],
                        }
                    ],
                )
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected path {request.url}")

    transport = httpx.MockTransport(handler)
    client = GammaClient("https://gamma-api.polymarket.com", transport=transport)

    markets = client.fetch_sports_markets(sport_codes={"epl"})

    assert len(markets) == 1
    assert markets[0].market_id == "market-1"
    assert markets[0].event_id == "event-1"
    assert markets[0].category == "sports"
    assert markets[0].outcomes == ("West Ham United FC", "Wolverhampton Wanderers FC")


def test_gamma_client_retries_transient_connect_error_for_sports_endpoint() -> None:
    attempts = {"sports": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/sports":
            attempts["sports"] += 1
            if attempts["sports"] == 1:
                raise httpx.ConnectError("transient eof", request=request)
            return httpx.Response(
                200,
                json=[{"sport": "epl", "tags": "1,82,306"}],
            )
        if request.url.path == "/events":
            return httpx.Response(200, json=[])
        raise AssertionError(f"unexpected path {request.url}")

    transport = httpx.MockTransport(handler)
    client = GammaClient(
        "https://gamma-api.polymarket.com",
        transport=transport,
        retry_backoff_seconds=0.0,
    )

    markets = client.fetch_sports_markets(sport_codes={"epl"})

    assert markets == []
    assert attempts["sports"] == 2
