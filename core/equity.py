from __future__ import annotations

from decimal import Decimal

from core.precision import q8


def recalculate_equity(equity_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    """Rebuild equity by applying all cashflow components row by row."""
    if not equity_rows:
        return []

    rows = sorted(equity_rows, key=lambda row: row.get("date"))
    equity = Decimal("0")

    for row in rows:
        profit = q8(row.get("profit", 0))
        funding_fee = q8(row.get("funding_fee", 0))
        trading_fee = q8(row.get("trading_fee", 0))
        deposit = q8(row.get("deposit", 0))
        withdraw = q8(row.get("withdraw", 0))

        delta = q8(profit + funding_fee - trading_fee + deposit - withdraw)
        equity = q8(equity + delta)
        row["equity"] = equity

    return rows
