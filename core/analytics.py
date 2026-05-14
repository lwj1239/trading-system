from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


EFFECTIVE_WIN_THRESHOLD = 0.01


def _max_streak(mask: list[bool]) -> int:
    max_count = 0
    current = 0
    for value in mask:
        if bool(value):
            current += 1
            max_count = max(max_count, current)
        else:
            current = 0
    return max_count


def _current_streak(mask: list[bool]) -> int:
    current = 0
    for value in reversed(mask):
        if bool(value):
            current += 1
        else:
            break
    return current


def build_analytics(trades_rows: list[dict[str, object]], nav_rows: list[dict[str, object]]) -> dict[str, Any]:
    trades_df = pd.DataFrame(trades_rows)
    if "profit" not in trades_df.columns:
        trades_df["profit"] = 0.0
    if "entry" not in trades_df.columns:
        trades_df["entry"] = 0.0
    if "size" not in trades_df.columns:
        trades_df["size"] = 0.0

    profits = pd.to_numeric(trades_df["profit"], errors="coerce").fillna(0.0)
    entries = pd.to_numeric(trades_df["entry"], errors="coerce").fillna(0.0).abs()
    sizes = pd.to_numeric(trades_df["size"], errors="coerce").fillna(0.0).abs()
    notionals = (entries * sizes).replace(0.0, np.nan)
    trade_returns = (profits / notionals).replace([np.inf, -np.inf], np.nan).fillna(0.0)

    total_trades = int(len(profits))
    wins = profits[profits > 0]
    losses = profits[profits < 0]

    win_rate = float(len(wins) / total_trades) if total_trades else 0.0
    avg_win = float(wins.mean()) if len(wins) else 0.0
    avg_loss = float(abs(losses.mean())) if len(losses) else 0.0
    payoff_ratio = (avg_win / avg_loss) if avg_loss > 0 else float("inf")

    total_profit = float(wins.sum())
    total_loss_abs = float(abs(losses.sum()))
    profit_factor = (total_profit / total_loss_abs) if total_loss_abs > 0 else float("inf")

    expectancy = float(profits.mean()) if total_trades else 0.0

    nav_df = pd.DataFrame(nav_rows)
    if "nav" not in nav_df.columns:
        nav_df["nav"] = 0.0
    if "drawdown" not in nav_df.columns:
        nav_df["drawdown"] = 0.0

    nav_values = pd.to_numeric(nav_df["nav"], errors="coerce").fillna(0.0)
    returns = nav_values.pct_change().replace([np.inf, -np.inf], np.nan).dropna()
    sharpe_ratio = 0.0
    if not returns.empty:
        std = float(returns.std(ddof=0))
        if std > 0:
            sharpe_ratio = float((np.sqrt(252) * returns.mean()) / std)

    max_win_streak = _max_streak((profits > 0).tolist())
    max_loss_streak = _max_streak((profits < 0).tolist())
    current_win_streak = _current_streak((profits > 0).tolist())
    current_loss_streak = _current_streak((profits < 0).tolist())
    effective_win_mask = (trade_returns >= EFFECTIVE_WIN_THRESHOLD).tolist()
    max_effective_win_streak = _max_streak(effective_win_mask)
    current_effective_win_streak = _current_streak(effective_win_mask)

    drawdowns = pd.to_numeric(nav_df["drawdown"], errors="coerce").fillna(0.0)
    max_drawdown = float(drawdowns.max()) if not drawdowns.empty else 0.0
    current_drawdown = float(drawdowns.iloc[-1]) if not drawdowns.empty else 0.0
    prev_drawdown = float(drawdowns.iloc[-2]) if len(drawdowns) >= 2 else current_drawdown
    latest_return = float(returns.iloc[-1]) if not returns.empty else 0.0
    daily_loss = abs(latest_return) if latest_return < 0 else 0.0

    result = {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": payoff_ratio,
        "profit_factor": profit_factor,
        "expectancy": float(expectancy),
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown": max_drawdown,
        "current_drawdown": current_drawdown,
        "max_win_streak": int(max_win_streak),
        "max_loss_streak": int(max_loss_streak),
        "current_win_streak": int(current_win_streak),
        "current_loss_streak": int(current_loss_streak),
        "max_effective_win_streak": int(max_effective_win_streak),
        "current_effective_win_streak": int(current_effective_win_streak),
        "effective_win_threshold": EFFECTIVE_WIN_THRESHOLD,
        "average_profit": float(profits.mean()) if total_trades else 0.0,
        "average_loss": float(losses.mean()) if len(losses) else 0.0,
        "equity_return": float(nav_values.iloc[-1] - 1.0) if not nav_values.empty else 0.0,
        "prev_drawdown": prev_drawdown,
        "daily_loss": daily_loss,
    }
    return result
