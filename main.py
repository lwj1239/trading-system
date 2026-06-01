from __future__ import annotations

import math
from decimal import Decimal
from pathlib import Path

from core.analytics import build_analytics
from core.data import EQUITY_COLUMNS, NAV_COLUMNS, ensure_demo_data, load_equity, load_trades, save_rows
from core.equity import recalculate_equity
from core.nav import build_nav
from core.risk import evaluate_risk, load_risk_state, save_risk_state


def _format_percent(value: float | Decimal) -> str:
    if isinstance(value, Decimal):
        percent = (value * Decimal("100")).quantize(Decimal("0.01"))
        return f"{percent}%"
    return f"{value * 100:.2f}%"


def _format_ratio(value: float | Decimal) -> str:
    if isinstance(value, Decimal):
        if value.is_infinite():
            return "INF"
        return f"{value:.3f}"
    if math.isinf(value):
        return "INF"
    return f"{value:.3f}"


def _format_as_of_date(equity_rows: list[dict[str, object]]) -> str | None:
    if not equity_rows:
        return None
    value = equity_rows[-1].get("date")
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    text = str(value)
    return text[:10] if text else None


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"

    trades_path, equity_path = ensure_demo_data(data_dir)
    trades_rows = load_trades(trades_path)
    equity_rows = load_equity(equity_path)

    equity_rows = recalculate_equity(equity_rows)
    nav_rows = build_nav(equity_rows)
    metrics = build_analytics(trades_rows, nav_rows)
    as_of_date = _format_as_of_date(equity_rows)
    risk_state_path = data_dir / "risk_state.json"
    risk_state = load_risk_state(risk_state_path)
    risk = evaluate_risk(metrics, risk_state, as_of_date=as_of_date)

    save_rows(equity_path, EQUITY_COLUMNS, equity_rows)
    save_rows(data_dir / "nav.csv", NAV_COLUMNS, nav_rows)
    save_risk_state(risk_state_path, risk["state"])

    print("=" * 60)
    print("Python 交易风控系统")
    print("=" * 60)
    print(f"交易笔数: {metrics['total_trades']}")
    print(f"胜率: {_format_percent(metrics['win_rate'])}")
    print(f"盈亏比: {_format_ratio(metrics['payoff_ratio'])}")
    print(f"Profit Factor: {metrics['profit_factor']:.3f}")
    print(
        "期望值: "
        f"{metrics['expectancy']:.3f} "
        f"(95% CI: [{metrics['expectancy_ci_low']:.3f}, {metrics['expectancy_ci_high']:.3f}])"
    )
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
    print(f"最大回撤: {_format_percent(metrics['max_drawdown'])}")
    print(f"当前回撤: {_format_percent(metrics['current_drawdown'])}")
    print(f"风险等级: Level {risk['level']}")
    print(f"当前风险: {_format_percent(risk['current_risk'])}")
    print(f"风控状态: {risk['status']}")

    if risk["actions"]:
        print("风险动作:")
        for action in risk["actions"]:
            print(f"- {action}")

    print(f"已输出: {equity_path.name}, nav.csv, risk_state.json")


if __name__ == "__main__":
    main()
