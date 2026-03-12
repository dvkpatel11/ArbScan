from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Flask, jsonify, render_template, request

from services.arbitrage import ArbitrageOpportunity, Leg, algorithm_effectiveness, build_opportunity, position_sizes
from services.sources import SourceClient


@dataclass
class RuntimeConfig:
    bankroll: float
    min_gross_margin_pct: float
    sport: str
    refresh_interval_seconds: int


app = Flask(__name__)
app.config["RUNTIME_CONFIG"] = RuntimeConfig(
    bankroll=float(os.getenv("DEFAULT_BANKROLL", "1000")),
    min_gross_margin_pct=float(os.getenv("MIN_GROSS_MARGIN_PCT", "0.5")),
    sport=os.getenv("SPORT", "soccer_epl"),
    refresh_interval_seconds=int(os.getenv("REFRESH_INTERVAL_SECONDS", "30")),
)


def _masked_key(value: str | None) -> str:
    if not value:
        return "(not set)"
    if len(value) <= 6:
        return "*" * len(value)
    return f"{value[:3]}...{value[-3:]}"


def collect_opportunities(bankroll: float, min_gross_margin_pct: float) -> tuple[List[ArbitrageOpportunity], Dict[str, int]]:
    client = SourceClient()
    try:
        normalized = client.normalize()
        feed_coverage = client.fetch_public_reference_feeds()
    finally:
        client.close()

    opportunities: List[ArbitrageOpportunity] = []
    for market_name, legs in normalized.items():
        best_by_side: Dict[str, Leg] = {}
        for leg in legs:
            current = best_by_side.get(leg.side)
            if current is None or leg.decimal_odds > current.decimal_odds:
                best_by_side[leg.side] = leg
        opportunity = build_opportunity(market_name, list(best_by_side.values()), bankroll=bankroll)
        if opportunity and opportunity.expected_edge_pct >= min_gross_margin_pct:
            opportunities.append(opportunity)

    opportunities.sort(key=lambda x: (x.expected_edge_pct, x.confidence_score), reverse=True)
    return opportunities, feed_coverage


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/config")
def api_config() -> Any:
    cfg: RuntimeConfig = app.config["RUNTIME_CONFIG"]
    return jsonify(
        {
            **asdict(cfg),
            "keys": {
                "odds_api_key": _masked_key(os.getenv("ODDS_API_KEY")),
                "polymarket_api_key": _masked_key(os.getenv("POLYMARKET_API_KEY")),
            },
        }
    )


@app.post("/api/config")
def api_update_config() -> Any:
    cfg: RuntimeConfig = app.config["RUNTIME_CONFIG"]
    payload = request.get_json(silent=True) or {}

    bankroll = float(payload.get("bankroll", cfg.bankroll))
    min_gross_margin_pct = float(payload.get("min_gross_margin_pct", cfg.min_gross_margin_pct))
    refresh_interval_seconds = int(payload.get("refresh_interval_seconds", cfg.refresh_interval_seconds))

    cfg.bankroll = max(bankroll, 1.0)
    cfg.min_gross_margin_pct = max(min_gross_margin_pct, 0.0)
    cfg.refresh_interval_seconds = max(refresh_interval_seconds, 5)

    return jsonify({"ok": True, "config": asdict(cfg)})


@app.get("/api/opportunities")
def api_opportunities() -> Any:
    cfg: RuntimeConfig = app.config["RUNTIME_CONFIG"]
    opportunities, coverage = collect_opportunities(
        bankroll=cfg.bankroll,
        min_gross_margin_pct=cfg.min_gross_margin_pct,
    )

    payload = []
    for opp in opportunities:
        stakes = position_sizes(cfg.bankroll, [leg.decimal_odds for leg in opp.legs])
        payload.append(
            {
                "market": opp.market,
                "implied_probability": round(opp.implied_probability, 4),
                "expected_edge_pct": opp.expected_edge_pct,
                "confidence_score": opp.confidence_score,
                "expected_profit_usd": opp.expected_profit_usd,
                "legs": [
                    {
                        "source": leg.source,
                        "side": leg.side,
                        "decimal_odds": leg.decimal_odds,
                        "liquidity_usd": leg.liquidity_usd,
                        "freshness_seconds": leg.freshness_seconds,
                        "recommended_stake": round(stakes[idx], 2),
                    }
                    for idx, leg in enumerate(opp.legs)
                ],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        )

    return jsonify(
        {
            "meta": {
                "bankroll": cfg.bankroll,
                "min_gross_margin_pct": cfg.min_gross_margin_pct,
                "refresh_interval_seconds": cfg.refresh_interval_seconds,
                "coverage": coverage,
                "algorithm_effectiveness": algorithm_effectiveness(opportunities),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            "opportunities": payload,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=False)
