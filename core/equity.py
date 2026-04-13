from __future__ import annotations

import pandas as pd

def recalculate_equity(equity_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Rebuild equity by applying all cashflow components row by row."""
    if not equity_rows:
        return []

    df = pd.DataFrame(equity_rows).copy()
    for col in ["profit", "funding_fee", "trading_fee", "deposit", "withdraw"]:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    delta = df["profit"] + df["funding_fee"] - df["trading_fee"] + df["deposit"] - df["withdraw"]
    df["equity"] = delta.cumsum()

    return df.to_dict(orient="records")
