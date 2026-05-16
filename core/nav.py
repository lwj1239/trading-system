from __future__ import annotations

from decimal import Decimal

from core.precision import q8


def build_nav(equity_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    if not equity_rows:
        raise ValueError("equity dataframe is empty")

    if "equity" not in equity_rows[0]:
        raise ValueError("equity column is required")

    rows = sorted(equity_rows, key=lambda row: row.get("date"))
    initial_equity = q8(rows[0].get("equity", 0))
    if initial_equity <= 0:
        raise ValueError("initial equity must be > 0 to compute nav")

    nav = Decimal("1")
    shares = initial_equity
    peak = nav
    result: list[dict[str, object]] = []

    for index, row in enumerate(rows):
        equity = q8(row.get("equity", 0))
        if index > 0:
            deposit = q8(row.get("deposit", 0))
            withdraw = q8(row.get("withdraw", 0))
            cashflow = q8(deposit - withdraw)
            if cashflow != 0:
                if nav <= 0:
                    raise ValueError("nav must be > 0 when applying cashflow")
                shares = q8(shares + (cashflow / nav))

        nav = q8(equity / shares) if shares > 0 else Decimal("0")
        peak = nav if nav > peak else peak
        drawdown = q8((peak - nav) / peak) if peak > 0 else Decimal("0")

        result.append({
            "date": row.get("date"),
            "equity": equity,
            "nav": nav,
            "peak": peak,
            "drawdown": drawdown,
        })

    return result
