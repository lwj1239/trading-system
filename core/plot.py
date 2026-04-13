from __future__ import annotations

from pathlib import Path


def plot_all(
    equity_rows: list[dict[str, object]],
    nav_rows: list[dict[str, object]],
    trades_rows: list[dict[str, object]],
    output_dir: Path,
) -> list[str]:
    """Render all required charts and return output file paths."""
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as exc:  # pragma: no cover
        raise RuntimeError(
            "matplotlib is required for plotting. Please run: uv add matplotlib"
        ) from exc

    saved: list[str] = []

    equity_dates = [row["date"] for row in equity_rows]
    equity_values = [float(row["equity"]) for row in equity_rows]
    nav_dates = [row["date"] for row in nav_rows]
    nav_values = [float(row["nav"]) for row in nav_rows]
    drawdown_values = [float(row["drawdown"]) for row in nav_rows]
    trade_profits = [float(row.get("profit", 0.0)) for row in trades_rows]

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(equity_dates, equity_values, color="#1f77b4", linewidth=2)
    ax.set_title("Equity Curve")
    ax.set_ylabel("Equity")
    ax.grid(alpha=0.3)
    path = output_dir / "equity_curve.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(nav_dates, nav_values, color="#2ca02c", linewidth=2)
    ax.set_title("NAV Curve")
    ax.set_ylabel("NAV")
    ax.grid(alpha=0.3)
    path = output_dir / "nav_curve.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.fill_between(nav_dates, drawdown_values, color="#d62728", alpha=0.6)
    ax.set_title("Drawdown Curve")
    ax.set_ylabel("Drawdown")
    ax.grid(alpha=0.3)
    path = output_dir / "drawdown_curve.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    saved.append(str(path))

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(trade_profits, bins=12, color="#9467bd", alpha=0.8, edgecolor="white")
    ax.set_title("Trade Profit Distribution")
    ax.set_xlabel("Profit")
    ax.grid(alpha=0.3)
    path = output_dir / "profit_distribution.png"
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    saved.append(str(path))

    return saved
