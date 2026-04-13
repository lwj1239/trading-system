from __future__ import annotations

from pathlib import Path

from core.analytics import build_analytics
from core.data import EQUITY_COLUMNS, ensure_demo_data, load_equity, load_trades, save_rows
from core.equity import recalculate_equity
from core.nav import build_nav
from core.plot import plot_all
from core.risk import evaluate_risk


def _format_percent(value: float) -> str:
    return f"{value * 100:.2f}%"


def main() -> None:
    project_dir = Path(__file__).resolve().parent
    data_dir = project_dir / "data"
    output_dir = project_dir / "output"

    trades_path, equity_path = ensure_demo_data(data_dir)
    trades_rows = load_trades(trades_path)
    equity_rows = load_equity(equity_path)

    equity_rows = recalculate_equity(equity_rows)
    nav_rows = build_nav(equity_rows)
    metrics = build_analytics(trades_rows, nav_rows)
    risk = evaluate_risk(metrics)

    save_rows(equity_path, EQUITY_COLUMNS, equity_rows)
    save_rows(data_dir / "nav.csv", ["date", "equity", "nav", "peak", "drawdown"], nav_rows)

    chart_paths: list[str] = []
    plot_error = ""
    try:
        chart_paths = plot_all(equity_rows, nav_rows, trades_rows, output_dir)
    except Exception as exc:
        plot_error = str(exc)

    print("=" * 60)
    print("Python 交易风控系统")
    print("=" * 60)
    print(f"交易笔数: {metrics['total_trades']}")
    print(f"胜率: {_format_percent(metrics['win_rate'])}")
    print(f"Profit Factor: {metrics['profit_factor']:.3f}")
    print(f"期望值: {metrics['expectancy']:.3f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']:.3f}")
    print(f"最大回撤: {_format_percent(metrics['max_drawdown'])}")
    print(f"当前回撤: {_format_percent(metrics['current_drawdown'])}")
    print(f"当前风险: {_format_percent(risk['current_risk'])}")
    print(f"风控状态: {risk['status']}")

    if risk["actions"]:
        print("风险动作:")
        for action in risk["actions"]:
            print(f"- {action}")

    print(f"已输出: {equity_path.name}, nav.csv")
    if chart_paths:
        print("图表输出:")
        for path in chart_paths:
            print(f"- {path}")
    elif plot_error:
        print(f"绘图跳过: {plot_error}")


if __name__ == "__main__":
    main()
