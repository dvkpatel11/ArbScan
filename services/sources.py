from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, List

import httpx
from pydantic import BaseModel, Field, ValidationError

from services.arbitrage import Leg

ODDS_API_BASE = "https://api.the-odds-api.com/v4/sports"
POLY_GAMMA = "https://gamma-api.polymarket.com/events"
POLY_CLOB = "https://clob.polymarket.com/prices-history"
ESPN_SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"
THESPORTSDB_EVENTS = "https://www.thesportsdb.com/api/v1/json/3/eventsnextleague.php"


class OddsOutcome(BaseModel):
    name: str
    price: float


class OddsMarket(BaseModel):
    outcomes: List[OddsOutcome] = Field(default_factory=list)


class OddsBookmaker(BaseModel):
    title: str = "Unknown"
    markets: List[OddsMarket] = Field(default_factory=list)


class OddsEvent(BaseModel):
    home_team: str
    away_team: str
    bookmakers: List[OddsBookmaker] = Field(default_factory=list)


class PolyEvent(BaseModel):
    title: str | None = None
    slug: str | None = None
    outcomes: List[str] = Field(default_factory=list)
    outcomePrices: List[str] = Field(default_factory=list)
    liquidity: float | None = None


class SourceClient:
    def __init__(self, timeout_seconds: float = 8.0) -> None:
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def fetch_odds_api(self) -> List[OddsEvent]:
        api_key = os.getenv("ODDS_API_KEY")
        if not api_key:
            return self._sample_odds_events()
        sport = os.getenv("SPORT", "soccer_epl")
        params = {"regions": "us", "markets": "h2h", "oddsFormat": "decimal", "apiKey": api_key}
        try:
            response = self._client.get(f"{ODDS_API_BASE}/{sport}/odds", params=params)
            response.raise_for_status()
            raw = response.json()
            return [OddsEvent.model_validate(item) for item in raw]
        except Exception:
            return self._sample_odds_events()

    def fetch_polymarket_gamma(self) -> List[PolyEvent]:
        try:
            response = self._client.get(POLY_GAMMA, params={"closed": "false", "limit": 50})
            response.raise_for_status()
            raw = response.json()
            return [PolyEvent.model_validate(item) for item in raw]
        except Exception:
            return self._sample_poly_events()

    def fetch_public_reference_feeds(self) -> Dict[str, int]:
        """Reference APIs used to estimate update latency and market coverage quality."""
        counts = {"espn_events": 0, "thesportsdb_events": 0}
        try:
            resp = self._client.get(ESPN_SCOREBOARD)
            resp.raise_for_status()
            counts["espn_events"] = len(resp.json().get("events", []))
        except Exception:
            pass
        try:
            resp = self._client.get(THESPORTSDB_EVENTS, params={"id": "4328"})
            resp.raise_for_status()
            counts["thesportsdb_events"] = len(resp.json().get("events", []))
        except Exception:
            pass
        return counts

    def normalize(self) -> Dict[str, List[Leg]]:
        result: Dict[str, List[Leg]] = {}

        for event in self.fetch_odds_api():
            market_name = f"{event.home_team} vs {event.away_team}"
            for bookmaker in event.bookmakers:
                for market in bookmaker.markets:
                    for outcome in market.outcomes:
                        result.setdefault(market_name, []).append(
                            Leg(
                                source=f"Sportsbook:{bookmaker.title}",
                                market=market_name,
                                side=outcome.name,
                                decimal_odds=outcome.price,
                                liquidity_usd=2000,
                                freshness_seconds=45,
                            )
                        )

        for event in self.fetch_polymarket_gamma():
            title = event.title or event.slug or "Unknown Market"
            for idx, side in enumerate(event.outcomes):
                try:
                    prob = float(event.outcomePrices[idx])
                    if prob <= 0:
                        continue
                except (ValueError, IndexError, ValidationError):
                    continue
                result.setdefault(title, []).append(
                    Leg(
                        source="Polymarket:Gamma",
                        market=title,
                        side=side,
                        decimal_odds=round(1 / prob, 4),
                        liquidity_usd=float(event.liquidity or 1000),
                        freshness_seconds=30,
                    )
                )

        return result

    @staticmethod
    def _sample_odds_events() -> List[OddsEvent]:
        return [
            OddsEvent(
                home_team="Arsenal",
                away_team="Chelsea",
                bookmakers=[
                    OddsBookmaker(
                        title="Book A",
                        markets=[OddsMarket(outcomes=[OddsOutcome(name="Arsenal", price=2.2), OddsOutcome(name="Chelsea", price=3.45)])],
                    ),
                    OddsBookmaker(
                        title="Book B",
                        markets=[OddsMarket(outcomes=[OddsOutcome(name="Arsenal", price=2.08), OddsOutcome(name="Chelsea", price=3.8)])],
                    ),
                ],
            )
        ]

    @staticmethod
    def _sample_poly_events() -> List[PolyEvent]:
        return [
            PolyEvent(
                title="Arsenal vs Chelsea",
                outcomes=["Arsenal", "Chelsea"],
                outcomePrices=["0.44", "0.57"],
                liquidity=12000,
            )
        ]
