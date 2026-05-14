from __future__ import annotations

import argparse
from pathlib import Path

from core.binance_sync import find_latest_binance_csv, parse_target_date, update_yesterday_equity


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="根据 Binance 流水自动更新昨日 equity")
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        help="目标日期，格式 YYYY-MM-DD，默认昨天",
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
