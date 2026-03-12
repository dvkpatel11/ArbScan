from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, List


@dataclass(frozen=True)
class Leg:
    source: str
    market: str
    side: str
    decimal_odds: float
    liquidity_usd: float = 0.0
    freshness_seconds: int = 60


@dataclass(frozen=True)
class ArbitrageOpportunity:
    market: str
    implied_probability: float
    expected_edge_pct: float
    confidence_score: float
    expected_profit_usd: float
    legs: List[Leg]


def american_to_decimal(american_price: int) -> float:
    if american_price == 0:
        raise ValueError("American odds cannot be 0")
    if american_price > 0:
        return 1 + (american_price / 100)
    return 1 + (100 / abs(american_price))


def implied_probabilities(decimal_odds: Iterable[float]) -> List[float]:
    odds = list(decimal_odds)
    if not odds:
        raise ValueError("At least one odd is required")
    return [1 / odd for odd in odds]


def arb_margin(decimal_odds: Iterable[float]) -> float:
    return sum(implied_probabilities(decimal_odds))


def expected_edge(decimal_odds: Iterable[float]) -> float:
    return (1 - arb_margin(decimal_odds)) * 100


def position_sizes(bankroll: float, decimal_odds: Iterable[float]) -> List[float]:
    odds = list(decimal_odds)
    margin = arb_margin(odds)
    if margin <= 0:
        raise ValueError("Invalid odds margin")
    total_payout = bankroll / margin
    return [total_payout / odd for odd in odds]


def expected_profit(bankroll: float, decimal_odds: Iterable[float]) -> float:
    odds = list(decimal_odds)
    stakes = position_sizes(bankroll, odds)
    payout = stakes[0] * odds[0]
    return payout - bankroll


def confidence_score(legs: List[Leg]) -> float:
    if not legs:
        return 0.0
    freshness = mean(max(0.0, 1 - min(leg.freshness_seconds, 300) / 300) for leg in legs)
    liquidity = mean(min(1.0, leg.liquidity_usd / 5000) for leg in legs)
    source_diversity = min(1.0, len({leg.source for leg in legs}) / max(1, len(legs)))
    return round((0.45 * freshness + 0.35 * liquidity + 0.20 * source_diversity) * 100, 2)


def build_opportunity(market: str, legs: List[Leg], bankroll: float) -> ArbitrageOpportunity | None:
    if len(legs) < 2:
        return None
    margin = arb_margin(leg.decimal_odds for leg in legs)
    if margin >= 1:
        return None
    odds = [leg.decimal_odds for leg in legs]
    return ArbitrageOpportunity(
        market=market,
        implied_probability=margin,
        expected_edge_pct=round((1 - margin) * 100, 4),
        confidence_score=confidence_score(legs),
        expected_profit_usd=round(expected_profit(bankroll, odds), 2),
        legs=legs,
    )


def algorithm_effectiveness(opportunities: List[ArbitrageOpportunity]) -> dict:
    if not opportunities:
        return {"count": 0, "avg_edge_pct": 0.0, "avg_confidence": 0.0}
    return {
        "count": len(opportunities),
        "avg_edge_pct": round(mean(o.expected_edge_pct for o in opportunities), 3),
        "avg_confidence": round(mean(o.confidence_score for o in opportunities), 2),
    }
