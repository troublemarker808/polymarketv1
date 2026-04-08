import json
from pathlib import Path

import httpx

from pm_bot.integrations.reference_odds.models import ReferenceOddsEventDTO
from pm_bot.integrations.reference_odds.translators import parse_reference_event


class TheOddsApiClient:
    def __init__(
        self,
        base_url: str,
        *,
        api_key: str | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(base_url=base_url, timeout=15.0, transport=transport)
        self._api_key = api_key

    def fetch_upcoming_h2h(self) -> list[ReferenceOddsEventDTO]:
        if not self._api_key:
            msg = "reference odds api key is required for live paper canary runs"
            raise ValueError(msg)
        response = self._client.get(
            "/sports/upcoming/odds",
            params={
                "apiKey": self._api_key,
                "regions": "us",
                "markets": "h2h",
                "oddsFormat": "decimal",
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            msg = "The Odds API returned a non-list payload"
            raise ValueError(msg)
        return [parse_reference_event(item) for item in payload]

    def load_fixture(self, path: Path) -> list[ReferenceOddsEventDTO]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, list):
            msg = "reference odds fixture must be a list"
            raise ValueError(msg)
        return [parse_reference_event(item) for item in payload]
