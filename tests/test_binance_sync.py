from __future__ import annotations

import csv
from datetime import date
from pathlib import Path

import pytest

from core.binance_sync import summarize_binance_cashflow, update_yesterday_equity


def _write_csv(path: Path, columns: list[str], rows: list[list[object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(columns)
        writer.writerows(rows)


def test_summarize_binance_cashflow_by_type(tmp_path: Path) -> None:
    binance_path = tmp_path / "Binance-合约交易流水-test.csv"
    _write_csv(
        binance_path,
        ["时间", "类型", "金额", "资产", "代币名称/币种名称/币对", "交易 ID"],
        [
            ["26-04-19 09:29:13", "COMMISSION", "-0.005999", "USDT", "SOLUSDT", "1"],
            ["26-04-19 09:29:13", "REALIZED_PNL", "-0.3682", "USDT", "SOLUSDT", "1"],
            ["26-04-19 08:00:02", "FUNDING_FEE", "0.00078926", "USDT", "SOLUSDT", "2"],
            ["26-04-18 08:00:02", "FUNDING_FEE", "999", "USDT", "SOLUSDT", "3"],
        ],
    )

    daily = summarize_binance_cashflow(binance_path, date(2026, 4, 19))

    assert float(daily.profit) == pytest.approx(-0.3682)
    assert float(daily.funding_fee) == pytest.approx(0.00078926)
    assert float(daily.trading_fee) == pytest.approx(0.005999)


def test_update_yesterday_equity_insert_or_update(tmp_path: Path) -> None:
    equity_path = tmp_path / "equity.csv"
    _write_csv(
        equity_path,
        ["date", "equity", "profit", "funding_fee", "trading_fee", "deposit", "withdraw", "note"],
        [
            ["2026-04-18", "32.50045678", "0", "0", "0", "0", "0", "前天基准"],
            ["2026-04-19", "0", "0", "0", "0", "1.0", "0", "手工补充入金"],
        ],
    )

    binance_path = tmp_path / "Binance-合约交易流水-test.csv"
    _write_csv(
        binance_path,
        ["时间", "类型", "金额", "资产", "代币名称/币种名称/币对", "交易 ID"],
        [
            ["26-04-19 09:29:13", "COMMISSION", "-0.005999", "USDT", "SOLUSDT", "1"],
            ["26-04-19 09:29:13", "REALIZED_PNL", "-0.3682", "USDT", "SOLUSDT", "1"],
            ["26-04-19 08:00:02", "FUNDING_FEE", "0.00078926", "USDT", "SOLUSDT", "2"],
            ["26-04-19 00:00:02", "FUNDING_FEE", "0.00097023", "USDT", "SOLUSDT", "3"],
        ],
    )

    result = update_yesterday_equity(
        equity_csv_path=equity_path,
        binance_csv_path=binance_path,
        target_date=date(2026, 4, 19),
    )

    expected_equity = 32.50045678 + (-0.3682) + (0.00078926 + 0.00097023) - 0.005999 + 1.0
    assert float(result["equity"]) == pytest.approx(expected_equity)

    with equity_path.open("r", encoding="utf-8") as file:
        rows = list(csv.DictReader(file))

    row = next(r for r in rows if r["date"] == "2026-04-19")
    assert float(row["profit"]) == pytest.approx(-0.3682)
    assert float(row["funding_fee"]) == pytest.approx(0.00175949)
    assert float(row["trading_fee"]) == pytest.approx(0.005999)
    assert float(row["deposit"]) == pytest.approx(1.0)
    assert row["equity"] == "33.12801727"
    assert row["note"] == "手工补充入金"


def test_summarize_binance_cashflow_transfer_and_deposit_withdraw(tmp_path: Path) -> None:
    binance_path = tmp_path / "Binance-合约交易流水-test.csv"
    _write_csv(
        binance_path,
        ["时间", "类型", "金额", "资产", "代币名称/币种名称/币对", "交易 ID"],
        [
            ["26-05-02 04:07:24", "TRANSFER", "116.78", "USDT", "", "1"],
            ["26-05-02 05:07:24", "TRANSFER", "-20", "USDT", "", "2"],
            ["26-05-02 06:07:24", "DEPOSIT", "5", "USDT", "", "3"],
            ["26-05-02 07:07:24", "WITHDRAW", "-3", "USDT", "", "4"],
        ],
    )

    daily = summarize_binance_cashflow(binance_path, date(2026, 5, 2))

    assert float(daily.deposit) == pytest.approx(121.78)
    assert float(daily.withdraw) == pytest.approx(23.0)


def test_update_yesterday_equity_idempotent_deposit_withdraw(tmp_path: Path) -> None:
    equity_path = tmp_path / "equity.csv"
    _write_csv(
        equity_path,
        ["date", "equity", "profit", "funding_fee", "trading_fee", "deposit", "withdraw", "note"],
        [
            ["2026-05-01", "100", "0", "0", "0", "0", "0", "base"],
        ],
    )

    binance_path = tmp_path / "Binance-合约交易流水-test.csv"
    _write_csv(
        binance_path,
        ["时间", "类型", "金额", "资产", "代币名称/币种名称/币对", "交易 ID"],
        [
            ["26-05-02 04:07:24", "TRANSFER", "10", "USDT", "", "1"],
        ],
    )

    result_first = update_yesterday_equity(
        equity_csv_path=equity_path,
        binance_csv_path=binance_path,
        target_date=date(2026, 5, 2),
    )
    result_second = update_yesterday_equity(
        equity_csv_path=equity_path,
        binance_csv_path=binance_path,
        target_date=date(2026, 5, 2),
    )

    assert result_first["deposit"] == result_second["deposit"]
    assert result_first["withdraw"] == result_second["withdraw"]
    assert result_first["equity"] == result_second["equity"]
