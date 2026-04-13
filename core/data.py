from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

TRADE_COLUMNS = [
    "date",
    "symbol",
    "side",
    "entry",
    "exit",
    "size",
    "profit",
    "risk",
    "setup",
    "notes",
]

EQUITY_COLUMNS = [
    "date",
    "equity",
    "profit",
    "funding_fee",
    "trading_fee",
    "deposit",
    "withdraw",
    "note",
]


def ensure_demo_data(data_dir: Path) -> tuple[Path, Path]:
    """Create demo csv files when user data does not exist."""
    data_dir.mkdir(parents=True, exist_ok=True)
    trades_path = data_dir / "trades.csv"
    equity_path = data_dir / "equity.csv"

    if not trades_path.exists():
        demo_trades = [
            ["2024-01-01", "BTCUSDT", "long", 42000, 42500, 0.50, 200, 0.020, "breakout", "good trade"],
            ["2024-01-03", "ETHUSDT", "short", 2450, 2400, 1.20, 120, 0.015, "mean_reversion", "clean setup"],
            ["2024-01-04", "BTCUSDT", "long", 43000, 42600, 0.35, -140, 0.020, "breakout", "invalidated"],
            ["2024-01-06", "SOLUSDT", "long", 95, 102, 30.0, 210, 0.018, "trend_follow", "momentum"],
            ["2024-01-08", "ETHUSDT", "short", 2510, 2575, 0.80, -90, 0.020, "news", "slippage"],
            ["2024-01-10", "BTCUSDT", "short", 43800, 43150, 0.45, 190, 0.015, "pullback", "discipline"],
        ]
        _write_rows(trades_path, TRADE_COLUMNS, demo_trades)

    if not equity_path.exists():
        demo_equity = [
            ["2024-01-01", 0, 0, 0, 0, 10000, 0, "initial deposit"],
            ["2024-01-02", 0, 200, -10, 3, 0, 0, "btc trade"],
            ["2024-01-03", 0, 120, -6, 2.5, 0, 0, "eth trade"],
            ["2024-01-04", 0, -140, -8, 2.5, 0, 0, "btc stop"],
            ["2024-01-05", 0, 0, -2, 1.2, 500, 0, "extra deposit"],
            ["2024-01-06", 0, 210, -7, 3, 0, 0, "sol trend"],
            ["2024-01-07", 0, 0, -5, 1.2, 0, 300, "withdraw"],
            ["2024-01-08", 0, -90, -6, 2, 0, 0, "eth loss"],
            ["2024-01-10", 0, 190, -4, 2.6, 0, 0, "btc short"],
        ]
        _write_rows(equity_path, EQUITY_COLUMNS, demo_equity)

    return trades_path, equity_path


def load_trades(path: Path) -> list[dict[str, object]]:
    df = _read_dataframe(path, TRADE_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="%Y-%m-%d")
    if df["date"].isna().any():
        raise ValueError(f"{path.name} contains invalid dates")

    numeric_cols = ["entry", "exit", "size", "profit", "risk"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.sort_values("date").reset_index(drop=True)
    return df.to_dict(orient="records")


def load_equity(path: Path) -> list[dict[str, object]]:
    df = _read_dataframe(path, EQUITY_COLUMNS)
    df["date"] = pd.to_datetime(df["date"], errors="coerce", format="%Y-%m-%d")
    if df["date"].isna().any():
        raise ValueError(f"{path.name} contains invalid dates")

    numeric_cols = ["equity", "profit", "funding_fee", "trading_fee", "deposit", "withdraw"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    df = df.sort_values("date").reset_index(drop=True)
    return df.to_dict(orient="records")


def save_rows(path: Path, columns: list[str], rows: list[dict[str, object]]) -> None:
    if not rows:
        pd.DataFrame(columns=columns).to_csv(path, index=False, encoding="utf-8")
        return

    df = pd.DataFrame(rows)
    for col in columns:
        if col not in df.columns:
            df[col] = ""
    df = df[columns]

    if "date" in df.columns:
        date_series = pd.to_datetime(df["date"], errors="coerce")
        df["date"] = date_series.dt.strftime("%Y-%m-%d").fillna(df["date"].astype(str))

    df.to_csv(path, index=False, encoding="utf-8")


def _read_dataframe(path: Path, expected_columns: list[str]) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8")
    missing = [col for col in expected_columns if col not in df.columns]
    if missing:
        raise ValueError(f"{path.name} missing required columns: {missing}")
    return df[expected_columns].copy()


def _write_rows(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)
