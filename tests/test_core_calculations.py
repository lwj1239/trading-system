from __future__ import annotations

from decimal import Decimal

import numpy as np
import pytest

from core.analytics import build_analytics
from core.equity import recalculate_equity
from core.nav import build_nav
from core.precision import q8
from core.risk import evaluate_risk


def test_recalculate_equity_and_build_nav() -> None:
    equity_rows = [
        {
            "date": "2024-01-01",
            "profit": 0,
            "funding_fee": 0,
            "trading_fee": 0,
            "deposit": 10000,
            "withdraw": 0,
        },
        {
            "date": "2024-01-02",
            "profit": 200,
            "funding_fee": -10,
            "trading_fee": 3,
            "deposit": 0,
            "withdraw": 0,
        },
        {
            "date": "2024-01-03",
            "profit": -100,
            "funding_fee": -5,
            "trading_fee": 2,
            "deposit": 0,
            "withdraw": 50,
        },
    ]

    recalculated = recalculate_equity(equity_rows)
    assert [row["equity"] for row in recalculated] == [
        Decimal("10000.00000000"),
        Decimal("10187.00000000"),
        Decimal("10030.00000000"),
    ]

    nav_rows = build_nav(recalculated)
    assert nav_rows[0]["nav"] == Decimal("1.00000000")
    nav_day1 = q8(Decimal("10187") / Decimal("10000"))
    assert nav_rows[1]["nav"] == nav_day1

    shares_after_withdraw = q8(Decimal("10000") + (Decimal("-50") / nav_day1))
    nav_day2 = q8(Decimal("10030") / shares_after_withdraw)
    expected_drawdown = q8((nav_day1 - nav_day2) / nav_day1)
    assert nav_rows[2]["drawdown"] == expected_drawdown


def test_build_nav_validation() -> None:
    with pytest.raises(ValueError, match="equity dataframe is empty"):
        build_nav([])

    with pytest.raises(ValueError, match="initial equity must be > 0"):
        build_nav([
            {"date": "2024-01-01", "equity": 0},
            {"date": "2024-01-02", "equity": 100},
        ])


def test_build_analytics_metrics() -> None:
    trades_rows = [
        {"profit": 100},
        {"profit": -50},
        {"profit": 200},
        {"profit": -25},
    ]
    nav_rows = [
        {"nav": 1.0, "drawdown": 0.0},
        {"nav": 1.1, "drawdown": 0.0},
        {"nav": 1.05, "drawdown": (1.1 - 1.05) / 1.1},
        {"nav": 1.2, "drawdown": 0.0},
    ]

    metrics = build_analytics(trades_rows, nav_rows)

    assert metrics["total_trades"] == 4
    assert float(metrics["win_rate"]) == pytest.approx(0.5)
    assert float(metrics["avg_win"]) == pytest.approx(150.0)
    assert float(metrics["avg_loss"]) == pytest.approx(37.5)
    assert float(metrics["payoff_ratio"]) == pytest.approx(4.0)
    assert float(metrics["profit_factor"]) == pytest.approx(4.0)
    assert float(metrics["expectancy"]) == pytest.approx(56.25)
    assert metrics["max_win_streak"] == 1
    assert metrics["max_loss_streak"] == 1
    assert float(metrics["max_drawdown"]) == pytest.approx((1.1 - 1.05) / 1.1)
    assert float(metrics["current_drawdown"]) == pytest.approx(0.0)
    assert float(metrics["equity_return"]) == pytest.approx(0.2)

    returns = np.array([0.1, (1.05 - 1.1) / 1.1, (1.2 - 1.05) / 1.05])
    expected_sharpe = np.sqrt(252) * returns.mean() / returns.std(ddof=0)
    assert float(metrics["sharpe_ratio"]) == pytest.approx(expected_sharpe)


def test_effective_win_streak_uses_return_threshold_strict_mode() -> None:
    trades_rows = [
        {"entry": 100, "size": 1, "profit": 0.3},
        {"entry": 100, "size": 1, "profit": 1.2},
        {"entry": 100, "size": 1, "profit": 0.8},
        {"entry": 100, "size": 1, "profit": 1.5},
        {"entry": 100, "size": 1, "profit": 1.1},
    ]
    nav_rows = [{"nav": 1.0, "drawdown": 0.0}]

    metrics = build_analytics(trades_rows, nav_rows)

    assert float(metrics["effective_win_threshold"]) == pytest.approx(0.01)
    assert metrics["current_effective_win_streak"] == 2
    assert metrics["max_effective_win_streak"] == 2


def test_risk_level_uses_highest_trigger() -> None:
    metrics = {
        "current_loss_streak": 2,
        "current_drawdown": 0.06,
        "current_win_streak": 0,
    }
    risk = evaluate_risk(metrics, {"level": 0, "last_drawdown": 0.06})

    assert risk["level"] == 2
    assert float(risk["current_risk"]) == pytest.approx(0.01)
    assert risk["status"] == "active"


def test_risk_recovery_downgrades_one_or_more_levels() -> None:
    metrics = {
        "current_loss_streak": 0,
        "current_drawdown": 0.04,
        "current_effective_win_streak": 2,
        "effective_win_threshold": 0.01,
    }
    risk = evaluate_risk(metrics, {"level": 3, "last_drawdown": 0.10})

    assert risk["level"] == 1
    assert float(risk["current_risk"]) == pytest.approx(0.015)


def test_risk_recovery_new_high_resets_to_level_zero() -> None:
    metrics = {
        "current_loss_streak": 0,
        "current_drawdown": 0.0,
        "current_effective_win_streak": 0,
        "effective_win_threshold": 0.01,
    }
    risk = evaluate_risk(metrics, {"level": 3, "last_drawdown": 0.06})

    assert risk["level"] == 0
    assert float(risk["current_risk"]) == pytest.approx(0.02)


def test_risk_level_four_stops_trading() -> None:
    metrics = {
        "current_loss_streak": 7,
        "current_drawdown": 0.02,
        "current_effective_win_streak": 0,
        "effective_win_threshold": 0.01,
    }
    risk = evaluate_risk(metrics, {"level": 0, "last_drawdown": 0.02}, as_of_date="2026-04-21")

    assert risk["level"] == 4
    assert float(risk["current_risk"]) == pytest.approx(0.0)
    assert risk["status"] == "stopped"


def test_level4_stops_for_two_days_then_back_to_level2() -> None:
    trigger_metrics = {
        "current_loss_streak": 7,
        "current_drawdown": 0.02,
        "current_effective_win_streak": 0,
        "effective_win_threshold": 0.01,
    }
    day0 = evaluate_risk(trigger_metrics, {"level": 0, "last_drawdown": 0.02}, as_of_date="2026-04-21")
    assert day0["level"] == 4
    assert day0["status"] == "stopped"

    mild_metrics = {
        "current_loss_streak": 0,
        "current_drawdown": 0.01,
        "current_effective_win_streak": 0,
        "effective_win_threshold": 0.01,
    }
    day1 = evaluate_risk(mild_metrics, day0["state"], as_of_date="2026-04-22")
    assert day1["level"] == 4
    assert day1["status"] == "stopped"

    day2 = evaluate_risk(mild_metrics, day1["state"], as_of_date="2026-04-23")
    assert day2["level"] == 2
    assert float(day2["current_risk"]) == pytest.approx(0.01)
    assert day2["status"] == "active"
