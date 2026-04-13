from __future__ import annotations

import pandas as pd

def build_nav(equity_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not equity_rows:
        raise ValueError("equity dataframe is empty")

    df = pd.DataFrame(equity_rows).copy()
    if "equity" not in df.columns:
        raise ValueError("equity column is required")

    df["equity"] = pd.to_numeric(df["equity"], errors="coerce").fillna(0.0)
    initial_equity = float(df["equity"].iloc[0])
    if initial_equity <= 0:
        raise ValueError("initial equity must be > 0 to compute nav")

    df["nav"] = df["equity"] / initial_equity
    df["peak"] = df["nav"].cummax()
    df["drawdown"] = ((df["peak"] - df["nav"]) / df["peak"]).fillna(0.0)

    return df[["date", "equity", "nav", "peak", "drawdown"]].to_dict(orient="records")
