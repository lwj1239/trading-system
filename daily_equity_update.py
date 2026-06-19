from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from core.binance_sync import (
    find_latest_binance_csv,
    rebuild_equity_from_earliest_binance_date,
    parse_target_date,
    rebuild_equity_from_date,
    update_yesterday_equity,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据 Binance 流水自动更新昨日 equity")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="目标日期，格式 YYYY-MM-DD，默认昨天",
    )
    parser.add_argument(
        "--rebuild-from",
        type=str,
        default=None,
        help="从指定日期开始重算 equity（包含当天），格式 YYYY-MM-DD",
    )
    parser.add_argument(
        "--backfill-to-today",
        action="store_true",
        help="自动读取最早流水日期，并一直回填到今天",
    )
    parser.add_argument(
        "--binance-csv",
        type=str,
        default=None,
        help="Binance 流水路径，默认自动选择项目目录下最新 Binance-合约交易流水-*.csv",
    )
    parser.add_argument(
        "--equity-csv",
        type=str,
        default="data/equity.csv",
        help="equity 文件路径，默认 data/equity.csv",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    project_dir = Path(__file__).resolve().parent
    target_date = parse_target_date(args.date)
    equity_csv_path = (project_dir / args.equity_csv).resolve()
    binance_csv_path = Path(args.binance_csv).resolve() if args.binance_csv else find_latest_binance_csv(project_dir)

    if args.backfill_to_today:
        if args.rebuild_from:
            raise ValueError("--backfill-to-today 不能与 --rebuild-from 同时使用")

        summary = rebuild_equity_from_earliest_binance_date(
            equity_csv_path=equity_csv_path,
            binance_csv_path=binance_csv_path,
            end_date=date.today(),
        )

        print("=" * 48)
        print("从最早流水日期回填 Equity 完成")
        print("=" * 48)
        print(f"开始日期: {summary['start_date']}")
        print(f"结束日期: {summary['end_date']}")
        print(f"基准日期: {summary['base_date']}")
        print(f"基准权益: {summary['base_equity']}")
        print(f"更新行数: {summary['rows_updated']}")
        print(f"最后日期: {summary['last_date']}")
        print(f"最后 equity: {summary['last_equity']}")
        print(f"已写入: {equity_csv_path}")
    elif args.rebuild_from:
        rebuild_from = parse_target_date(args.rebuild_from)
        summary = rebuild_equity_from_date(
            equity_csv_path=equity_csv_path,
            binance_csv_path=binance_csv_path,
            start_date=rebuild_from,
            end_date=target_date,
        )

        print("=" * 48)
        print("区间 Equity 重新计算完成")
        print("=" * 48)
        print(f"开始日期: {summary['start_date']}")
        print(f"结束日期: {summary['end_date']}")
        print(f"基准日期: {summary['base_date']}")
        print(f"基准权益: {summary['base_equity']}")
        print(f"更新行数: {summary['rows_updated']}")
        print(f"最后日期: {summary['last_date']}")
        print(f"最后 equity: {summary['last_equity']}")
        print(f"已写入: {equity_csv_path}")
    else:
        summary = update_yesterday_equity(
            equity_csv_path=equity_csv_path,
            binance_csv_path=binance_csv_path,
            target_date=target_date,
        )

        print("=" * 48)
        print("昨日 Equity 自动更新完成")
        print("=" * 48)
        print(f"目标日期: {summary['date']}")
        print(f"基准日期: {summary['base_date']}")
        print(f"基准权益: {summary['base_equity']}")
        print(f"profit: {summary['profit']}")
        print(f"funding_fee: {summary['funding_fee']}")
        print(f"trading_fee: {summary['trading_fee']}")
        print(f"deposit: {summary['deposit']}")
        print(f"withdraw: {summary['withdraw']}")
        print(f"更新后 equity: {summary['equity']}")
        print(f"已写入: {equity_csv_path}")


if __name__ == "__main__":
    main()
