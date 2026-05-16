from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from decimal import Decimal

import pytest

from core.data import EQUITY_COLUMNS, TRADE_COLUMNS, load_equity, load_trades, save_rows


def _write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)


def test_load_trades_parses_sorts_and_coerces_numeric(tmp_path: Path) -> None:
    trades_path = tmp_path / "trades.csv"
    _write_csv(
        trades_path,
        TRADE_COLUMNS,
        [
            ["2024-01-03", "BTCUSDT", "long", "42000", "42500", "0.5", "200", "0.02", "breakout", "ok"],
            ["2024-01-01", "ETHUSDT", "short", "bad", "2400", "1.2", "120", "0.01", "mean", "ok"],
        ],
    )

    rows = load_trades(trades_path)

    assert rows[0]["date"] < rows[1]["date"]
    assert isinstance(rows[0]["date"], datetime)
    assert rows[0]["entry"] == Decimal("0")
    assert rows[1]["entry"] == Decimal("42000.00000000")


def test_load_trades_invalid_date_raises(tmp_path: Path) -> None:
    trades_path = tmp_path / "trades.csv"
    _write_csv(
        trades_path,
        TRADE_COLUMNS,
        [["2024/01/01", "BTCUSDT", "long", "1", "2", "1", "1", "0.01", "x", "x"]],
    )

    with pytest.raises(ValueError, match="contains invalid dates"):
        load_trades(trades_path)


def test_load_equity_coerces_numeric(tmp_path: Path) -> None:
    equity_path = tmp_path / "equity.csv"
    _write_csv(
        equity_path,
        EQUITY_COLUMNS,
        [["2024-01-01", "bad", "200", "-10", "3", "0", "0", "note"]],
    )

    rows = load_equity(equity_path)
    assert rows[0]["equity"] == Decimal("0")
    assert rows[0]["profit"] == Decimal("200.00000000")


def test_save_rows_formats_date_and_keeps_columns(tmp_path: Path) -> None:
    output_path = tmp_path / "out.csv"
    rows = [
        {
            "date": datetime(2024, 1, 1),
            "equity": 10000,
            "profit": 0,
            "funding_fee": 0,
            "trading_fee": 0,
            "deposit": 10000,
            "withdraw": 0,
            "note": "init",
        }
    ]

    save_rows(output_path, EQUITY_COLUMNS, rows)

    with output_path.open("r", newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        parsed = list(reader)

    assert reader.fieldnames == EQUITY_COLUMNS
    assert parsed[0]["date"] == "2024-01-01"
    assert parsed[0]["equity"] == "10000.00000000"
