from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

from core.data import load_equity, save_rows
from core.precision import format_8, q8


@dataclass(frozen=True)
class DailyCashflow:
    date: date
    profit: Decimal
    funding_fee: Decimal
    trading_fee: Decimal
    deposit: Decimal
    withdraw: Decimal


def _fmt_decimal(value: Decimal) -> str:
    return format_8(value)


def parse_target_date(raw: str | None) -> date:
    if raw is None:
        return date.today() - timedelta(days=1)
    return datetime.strptime(raw, "%Y-%m-%d").date()


def find_latest_binance_csv(project_dir: Path) -> Path:
    candidates = sorted(project_dir.glob("Binance-合约交易流水-*.csv"), key=lambda p: p.stat().st_mtime)
    if not candidates:
        raise FileNotFoundError("未找到 Binance 交易流水文件，文件名需匹配 Binance-合约交易流水-*.csv")
    return candidates[-1]


def _load_binance_df(binance_csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(binance_csv_path, encoding="utf-8-sig")

    required = ["时间", "类型", "金额"]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"{binance_csv_path.name} 缺少字段: {missing}")

    df["时间"] = pd.to_datetime(df["时间"], errors="coerce", format="%y-%m-%d %H:%M:%S")
    if df["时间"].isna().any():
        raise ValueError(f"{binance_csv_path.name} 存在无法解析的时间，格式应为 yy-mm-dd HH:MM:SS")

    df["金额"] = df["金额"].map(q8)
    return df


def _summarize_daily_df(daily: pd.DataFrame, target_date: date) -> DailyCashflow:
    if daily.empty:
        return DailyCashflow(
            date=target_date,
            profit=Decimal("0"),
            funding_fee=Decimal("0"),
            trading_fee=Decimal("0"),
            deposit=Decimal("0"),
            withdraw=Decimal("0"),
        )

    profit = q8(sum(daily.loc[daily["类型"] == "REALIZED_PNL", "金额"], Decimal("0")))
    funding_fee = q8(sum(daily.loc[daily["类型"] == "FUNDING_FEE", "金额"], Decimal("0")))
    commission_sum = q8(sum(daily.loc[daily["类型"] == "COMMISSION", "金额"], Decimal("0")))
    trading_fee = q8(-commission_sum)

    deposit = Decimal("0")
    withdraw = Decimal("0")
    deposit_types = {"DEPOSIT"}
    withdraw_types = {"WITHDRAW", "WITHDRAWAL"}
    transfer_types = {"TRANSFER"}

    for _, row in daily.iterrows():
        flow_type = row["类型"]
        amount = q8(row["金额"])
        if flow_type in deposit_types:
            deposit = q8(deposit + amount)
        elif flow_type in withdraw_types:
            withdraw = q8(withdraw + abs(amount))
        elif flow_type in transfer_types:
            if amount >= 0:
                deposit = q8(deposit + amount)
            else:
                withdraw = q8(withdraw + abs(amount))

    return DailyCashflow(
        date=target_date,
        profit=profit,
        funding_fee=funding_fee,
        trading_fee=trading_fee,
        deposit=deposit,
        withdraw=withdraw,
    )


def summarize_binance_cashflow(binance_csv_path: Path, target_date: date) -> DailyCashflow:
    df = _load_binance_df(binance_csv_path)
    daily = df[df["时间"].dt.date == target_date]
    return _summarize_daily_df(daily, target_date)


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
    existing_deposit = q8(existing_row["deposit"]) if existing_row else Decimal("0")
    existing_withdraw = q8(existing_row["withdraw"]) if existing_row else Decimal("0")
    note = str(existing_row["note"]) if existing_row and existing_row.get("note") else "自动由 Binance 流水更新"

    deposit = daily.deposit if daily.deposit != Decimal("0") else existing_deposit
    withdraw = daily.withdraw if daily.withdraw != Decimal("0") else existing_withdraw

    base_equity = q8(base_row["equity"])
    new_equity = q8(base_equity + daily.profit + daily.funding_fee - daily.trading_fee + deposit - withdraw)

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


def rebuild_equity_from_date(
    equity_csv_path: Path,
    binance_csv_path: Path,
    start_date: date,
    end_date: date,
) -> dict[str, str | int]:
    if end_date < start_date:
        raise ValueError("结束日期不能早于开始日期。")

    base_date = start_date - timedelta(days=1)
    equity_rows = load_equity(equity_csv_path)

    base_row = next((row for row in equity_rows if row["date"].date() == base_date), None)
    if base_row is None:
        raise ValueError(f"缺少基准日权益: {base_date}. 请先保证前一天 equity 已存在。")

    df = _load_binance_df(binance_csv_path)
    df["date_only"] = df["时间"].dt.date
    range_df = df[(df["date_only"] >= start_date) & (df["date_only"] <= end_date)]

    grouped = {day: day_df for day, day_df in range_df.groupby("date_only")}
    kept_rows = [row for row in equity_rows if row["date"].date() < start_date]

    current_equity = q8(base_row["equity"])
    current_date = start_date
    updated_rows: list[dict[str, object]] = []

    while current_date <= end_date:
        daily_df = grouped.get(current_date, pd.DataFrame())
        daily = _summarize_daily_df(daily_df, current_date)

        existing_row = next((row for row in equity_rows if row["date"].date() == current_date), None)
        existing_deposit = q8(existing_row["deposit"]) if existing_row else Decimal("0")
        existing_withdraw = q8(existing_row["withdraw"]) if existing_row else Decimal("0")
        note = str(existing_row["note"]) if existing_row and existing_row.get("note") else "自动由 Binance 流水更新"

        deposit = daily.deposit if daily.deposit != Decimal("0") else existing_deposit
        withdraw = daily.withdraw if daily.withdraw != Decimal("0") else existing_withdraw

        current_equity = q8(
            current_equity
            + daily.profit
            + daily.funding_fee
            - daily.trading_fee
            + deposit
            - withdraw
        )

        updated_rows.append(
            {
                "date": pd.Timestamp(current_date),
                "equity": current_equity,
                "profit": daily.profit,
                "funding_fee": daily.funding_fee,
                "trading_fee": daily.trading_fee,
                "deposit": deposit,
                "withdraw": withdraw,
                "note": note,
            }
        )

        current_date += timedelta(days=1)

    kept_rows.extend(updated_rows)
    kept_rows = sorted(kept_rows, key=lambda row: row["date"])

    save_rows(
        equity_csv_path,
        ["date", "equity", "profit", "funding_fee", "trading_fee", "deposit", "withdraw", "note"],
        kept_rows,
    )

    last = updated_rows[-1] if updated_rows else None
    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "base_date": base_date.isoformat(),
        "base_equity": _fmt_decimal(q8(base_row["equity"])),
        "rows_updated": len(updated_rows),
        "last_date": last["date"].strftime("%Y-%m-%d") if last else "",
        "last_equity": _fmt_decimal(last["equity"]) if last else "0",
    }
