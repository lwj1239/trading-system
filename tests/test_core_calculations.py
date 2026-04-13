from __future__ import annotations

import numpy as np
import pytest

from core.analytics import build_analytics
from core.equity import recalculate_equity
from core.nav import build_nav


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
    assert [row["equity"] for row in recalculated] == pytest.approx([10000.0, 10187.0, 10030.0])

    nav_rows = build_nav(recalculated)
    assert nav_rows[0]["nav"] == pytest.approx(1.0)
    assert nav_rows[1]["nav"] == pytest.approx(1.0187)
    assert nav_rows[2]["drawdown"] == pytest.approx((1.0187 - 1.003) / 1.0187)


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
    assert metrics["win_rate"] == pytest.approx(0.5)
    assert metrics["avg_win"] == pytest.approx(150.0)
    assert metrics["avg_loss"] == pytest.approx(37.5)
    assert metrics["payoff_ratio"] == pytest.approx(4.0)
    assert metrics["profit_factor"] == pytest.approx(4.0)
    assert metrics["expectancy"] == pytest.approx(56.25)
    assert metrics["max_win_streak"] == 1
    assert metrics["max_loss_streak"] == 1
    assert metrics["max_drawdown"] == pytest.approx((1.1 - 1.05) / 1.1)
    assert metrics["current_drawdown"] == pytest.approx(0.0)
    assert metrics["equity_return"] == pytest.approx(0.2)

    returns = np.array([0.1, (1.05 - 1.1) / 1.1, (1.2 - 1.05) / 1.05])
    expected_sharpe = np.sqrt(252) * returns.mean() / returns.std(ddof=0)
    assert metrics["sharpe_ratio"] == pytest.approx(expected_sharpe)
