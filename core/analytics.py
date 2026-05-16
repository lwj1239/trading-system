from __future__ import annotations

from decimal import Decimal
from typing import Any

from core.precision import q8


EFFECTIVE_WIN_THRESHOLD = Decimal("0.01")


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
    profits: list[Decimal] = []
    trade_returns: list[Decimal] = []

    for row in trades_rows:
        profit = q8(row.get("profit", 0))
        entry = q8(row.get("entry", 0))
        size = q8(row.get("size", 0))

        notional = q8(abs(entry) * abs(size))
        if notional == 0:
            trade_return = Decimal("0")
        else:
            trade_return = q8(profit / notional)

        profits.append(profit)
        trade_returns.append(trade_return)

    total_trades = int(len(profits))
    wins = [value for value in profits if value > 0]
    losses = [value for value in profits if value < 0]

    def _mean(values: list[Decimal]) -> Decimal:
        if not values:
            return Decimal("0")
        return q8(sum(values, Decimal("0")) / Decimal(len(values)))

    def _std(values: list[Decimal]) -> Decimal:
        if not values:
            return Decimal("0")
        mean = sum(values, Decimal("0")) / Decimal(len(values))
        variance = sum((value - mean) ** 2 for value in values) / Decimal(len(values))
        return q8(variance.sqrt()) if variance > 0 else Decimal("0")

    win_rate = q8(Decimal(len(wins)) / Decimal(total_trades)) if total_trades else Decimal("0")
    avg_win = _mean(wins)
    avg_loss = q8(abs(_mean(losses)))
    payoff_ratio = q8(avg_win / avg_loss) if avg_loss > 0 else Decimal("Infinity")

    total_profit = q8(sum(wins, Decimal("0")))
    total_loss_abs = q8(abs(sum(losses, Decimal("0"))))
    profit_factor = q8(total_profit / total_loss_abs) if total_loss_abs > 0 else Decimal("Infinity")

    expectancy = _mean(profits) if total_trades else Decimal("0")

    nav_values = [q8(row.get("nav", 0)) for row in nav_rows]
    returns: list[Decimal] = []
    for index in range(1, len(nav_values)):
        prev = nav_values[index - 1]
        if prev > 0:
            returns.append(q8((nav_values[index] / prev) - Decimal("1")))

    sharpe_ratio = Decimal("0")
    if returns:
        std = _std(returns)
        if std > 0:
            mean_return = _mean(returns)
            sharpe_ratio = q8((Decimal("252").sqrt() * mean_return) / std)

    max_win_streak = _max_streak([value > 0 for value in profits])
    max_loss_streak = _max_streak([value < 0 for value in profits])
    current_win_streak = _current_streak([value > 0 for value in profits])
    current_loss_streak = _current_streak([value < 0 for value in profits])
    effective_win_mask = [value >= EFFECTIVE_WIN_THRESHOLD for value in trade_returns]
    max_effective_win_streak = _max_streak(effective_win_mask)
    current_effective_win_streak = _current_streak(effective_win_mask)

    drawdowns = [q8(row.get("drawdown", 0)) for row in nav_rows]
    max_drawdown = max(drawdowns) if drawdowns else Decimal("0")
    current_drawdown = drawdowns[-1] if drawdowns else Decimal("0")
    prev_drawdown = drawdowns[-2] if len(drawdowns) >= 2 else current_drawdown
    latest_return = returns[-1] if returns else Decimal("0")
    daily_loss = abs(latest_return) if latest_return < 0 else Decimal("0")

    result = {
        "total_trades": total_trades,
        "win_rate": win_rate,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "payoff_ratio": payoff_ratio,
        "profit_factor": profit_factor,
        "expectancy": expectancy,
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
        "average_profit": _mean(profits) if total_trades else Decimal("0"),
        "average_loss": _mean(losses) if losses else Decimal("0"),
        "equity_return": q8(nav_values[-1] - Decimal("1")) if nav_values else Decimal("0"),
        "prev_drawdown": prev_drawdown,
        "daily_loss": daily_loss,
    }
    return result
