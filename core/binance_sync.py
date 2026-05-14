from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core.data import load_equity, save_rows


@dataclass(frozen=True)
class DailyCashflow:
    date: date
    profit: Decimal
    funding_fee: Decimal
    trading_fee: Decimal
    deposit: Decimal
    withdraw: Decimal


_Q8 = Decimal("0.00000001")


def _to_decimal(value: object) -> Decimal:
    text = str(value).strip()
    if text == "" or text.lower() in {"nan", "none"}:
        return Decimal("0")
    try:
        return Decimal(text)
    except Exception:
        return Decimal("0")


def _q8(value: Decimal) -> Decimal:
    return value.quantize(_Q8, rounding=ROUND_HALF_UP)


def _fmt_decimal(value: Decimal) -> str:
    text = format(_q8(value), "f").rstrip("0").rstrip(".")
    if "." not in text:
        return f"{text}.0"
    return text


def parse_target_date(raw: str | None) -> date:
    if raw is None:
        return date.today() - timedelta(days=1)
    return datetime.strptime(raw, "%Y-%m-%d").date()


def find_latest_binance_csv(project_dir: Path) -> Path:
    candidates = sorted(project_dir.glob("Binance-合约交易流水-*.csv"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError("未找到 Binance 交易流水文件，文件名需匹配 Binance-合约交易流水-*.csv")
    return candidates[-1]


def summarize_binance_cashflow(binance_csv_path: Path, target_date: date) -> DailyCashflow:
    df = pd.read_csv(binance_csv_path, encoding="utf-8-sig")

    required = ["时间", "类型", "金额"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{binance_csv_path.name} 缺少字段: {missing}")

    df["时间"] = pd.to_datetime(df["时间"], errors="coerce", format="%y-%m-%d %H:%M:%S")
    if df["时间"].isna().any():
        raise ValueError(f"{binance_csv_path.name} 存在无法解析的时间，格式应为 yy-mm-dd HH:MM:SS")

    df["金额"] = df["金额"].map(_to_decimal)
    daily = df[df["时间"].dt.date == target_date]

    profit = sum(daily.loc[daily["类型"] == "REALIZED_PNL", "金额"], Decimal("0"))
    funding_fee = sum(daily.loc[daily["类型"] == "FUNDING_FEE", "金额"], Decimal("0"))
    commission_sum = sum(daily.loc[daily["类型"] == "COMMISSION", "金额"], Decimal("0"))
    trading_fee = -commission_sum

    deposit = Decimal("0")
    withdraw = Decimal("0")
    deposit_types = {"DEPOSIT"}
    withdraw_types = {"WITHDRAW", "WITHDRAWAL"}
    transfer_types = {"TRANSFER"}

    for _, row in daily.iterrows():
        flow_type = row["类型"]
        amount = row["金额"]
        if flow_type in deposit_types:
            deposit += amount
        elif flow_type in withdraw_types:
            withdraw += abs(amount)
        elif flow_type in transfer_types:
            if amount >= 0:
                deposit += amount
            else:
                withdraw += abs(amount)

    return DailyCashflow(
        date=target_date,
        profit=profit,
        funding_fee=funding_fee,
        trading_fee=trading_fee,
        deposit=deposit,
        withdraw=withdraw,
    )


def update_yesterday_equity(
    equity_csv_path: Path,
    binance_csv_path: Path,
    target_date: date,
) -> dict[str, str]:
    base_date = target_date - timedelta(days=1)
    equity_rows = load_equity(equity_csv_path)
    daily = summarize_binance_cashflow(binance_csv_path, target_date)

    base_row = next((row for row in equity_rows if row["date"].date() == base_date), None)
    if base_row is None:
        raise ValueError(f"缺少基准日权益: {base_date}. 请先保证前一天(前天) equity 已存在。")

    existing_row = next((row for row in equity_rows if row["date"].date() == target_date), None)
    existing_deposit = _to_decimal(existing_row["deposit"]) if existing_row else Decimal("0")
    existing_withdraw = _to_decimal(existing_row["withdraw"]) if existing_row else Decimal("0")
    note = str(existing_row["note"]) if existing_row and existing_row.get("note") else "自动由 Binance 流水更新"

    deposit = daily.deposit if daily.deposit != Decimal("0") else existing_deposit
    withdraw = daily.withdraw if daily.withdraw != Decimal("0") else existing_withdraw

    base_equity = _to_decimal(base_row["equity"])
    new_equity = base_equity + daily.profit + daily.funding_fee - daily.trading_fee + deposit - withdraw

    new_row = {
        "date": pd.Timestamp(target_date),
        "equity": _fmt_decimal(new_equity),
        "profit": _fmt_decimal(daily.profit),
        "funding_fee": _fmt_decimal(daily.funding_fee),
        "trading_fee": _fmt_decimal(daily.trading_fee),
        "deposit": _fmt_decimal(deposit),
        "withdraw": _fmt_decimal(withdraw),
        "note": note,
    }

    kept_rows = [row for row in equity_rows if row["date"].date() != target_date]
    kept_rows.append(new_row)
    kept_rows = sorted(kept_rows, key=lambda row: row["date"])

    save_rows(
        equity_csv_path,
        ["date", "equity", "profit", "funding_fee", "trading_fee", "deposit", "withdraw", "note"],
        kept_rows,
    )

    return {
        "date": target_date.isoformat(),
        "base_date": base_date.isoformat(),
        "base_equity": _fmt_decimal(base_equity),
        "profit": _fmt_decimal(daily.profit),
        "funding_fee": _fmt_decimal(daily.funding_fee),
        "trading_fee": _fmt_decimal(daily.trading_fee),
        "deposit": _fmt_decimal(deposit),
        "withdraw": _fmt_decimal(withdraw),
        "equity": _fmt_decimal(new_equity),
    }
