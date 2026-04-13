from __future__ import annotations

from typing import Any


def evaluate_risk(metrics: dict[str, Any]) -> dict[str, Any]:
    base_risk = 0.02
    current_risk = base_risk
    actions: list[str] = []

    equity_return = float(metrics.get("equity_return", 0.0))
    if equity_return >= 0.10:
        actions.append("盈利达到10%，停止交易一天")
    elif equity_return >= 0.08:
        current_risk = min(current_risk, 0.01)
        actions.append("盈利达到8%，风险降至1%")
    elif equity_return >= 0.05:
        current_risk = min(current_risk, 0.015)
        actions.append("盈利达到5%，风险降至1.5%")

    max_loss_streak = int(metrics.get("max_loss_streak", 0))
    if max_loss_streak >= 5:
        actions.append("连续亏损5次，停止交易一周")
    elif max_loss_streak >= 3:
        actions.append("连续亏损3次，停止交易一天")

    drawdown = float(metrics.get("current_drawdown", 0.0))
    if drawdown >= 0.10:
        current_risk = 0.0
        actions.append("回撤达到10%，停止交易")
    elif drawdown >= 0.08:
        current_risk = min(current_risk, 0.01)
        actions.append("回撤达到8%，风险降至1%")
    elif drawdown >= 0.05:
        current_risk = min(current_risk, base_risk * 0.5)
        actions.append("回撤达到5%，风险减半")

    return {
        "base_risk": base_risk,
        "current_risk": current_risk,
        "actions": actions,
        "status": "stopped" if current_risk == 0 else "active",
    }
