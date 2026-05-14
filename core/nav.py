from __future__ import annotations

import pandas as pd


def build_nav(equity_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not equity_rows:
        raise ValueError("equity dataframe is empty")

    df = pd.DataFrame(equity_rows).copy()
    if "equity" not in df.columns:
        raise ValueError("equity column is required")

    for col in ["equity", "deposit", "withdraw"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    initial_equity = float(df["equity"].iloc[0])
    if initial_equity <= 0:
        raise ValueError("initial equity must be > 0 to compute nav")

    nav_values: list[float] = []
    shares_values: list[float] = []
    nav = 1.0
    shares = initial_equity

    for index, row in df.iterrows():
        equity = float(row["equity"])
        if index > 0:
            cashflow = float(row["deposit"]) - float(row["withdraw"])
            if cashflow != 0.0:
                if nav <= 0:
                    raise ValueError("nav must be > 0 when applying cashflow")
                shares += cashflow / nav
        nav = equity / shares if shares > 0 else 0.0
        nav_values.append(nav)
        shares_values.append(shares)

    df["nav"] = nav_values
    df["peak"] = pd.Series(nav_values).cummax().values
    df["drawdown"] = ((df["peak"] - df["nav"]) / df["peak"]).fillna(0.0)

    return df[["date", "equity", "nav", "peak", "drawdown"]].to_dict(orient="records")
