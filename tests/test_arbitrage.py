from services.arbitrage import (
    Leg,
    algorithm_effectiveness,
    arb_margin,
    build_opportunity,
    confidence_score,
    position_sizes,
)


def test_arb_margin_detects_positive_edge() -> None:
    assert arb_margin([2.2, 2.2]) < 1


def test_position_sizes_returns_balanced_payout() -> None:
    stakes = position_sizes(1000, [2.1, 2.1])
    assert round(stakes[0] * 2.1, 2) == round(stakes[1] * 2.1, 2)


def test_build_opportunity_requires_edge() -> None:
    no_edge = build_opportunity("x", [Leg("a", "x", "Yes", 1.9), Leg("b", "x", "No", 1.9)], bankroll=1000)
    assert no_edge is None


def test_confidence_score_increases_with_better_inputs() -> None:
    low = confidence_score([Leg("a", "m", "yes", 2.0, liquidity_usd=100, freshness_seconds=280)])
    high = confidence_score([Leg("a", "m", "yes", 2.0, liquidity_usd=9000, freshness_seconds=5)])
    assert high > low


def test_algorithm_effectiveness_summary() -> None:
    opp = build_opportunity("x", [Leg("a", "x", "A", 2.2), Leg("b", "x", "B", 2.2)], bankroll=1000)
    assert opp is not None
    summary = algorithm_effectiveness([opp])
    assert summary["count"] == 1
    assert summary["avg_edge_pct"] > 0
