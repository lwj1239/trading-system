# Python 交易风控系统

基于双表架构实现的交易风控系统，支持：

- 交易记录管理（trades）
- 资金流水管理（equity，含 funding fee / trading fee / deposit / withdraw）
- 资金曲线与净值回撤计算
- 统计指标（胜率、盈亏比、Profit Factor、Expectancy、Sharpe、连续盈亏）
- 规则化风控输出

## 项目结构

```text
system/
├── core/
│   ├── data.py
│   ├── equity.py
│   ├── nav.py
│   ├── analytics.py
│   └── risk.py
├── data/
│   ├── trades.csv
│   ├── equity.csv
│   └── nav.csv
├── tests/
│   ├── conftest.py
│   ├── test_binance_sync.py
│   ├── test_core_calculations.py
│   └── test_data_layer.py
└── main.py
```

## 运行

1. 安装依赖（核心计算基于 pandas/numpy，统计扩展支持 scipy）

推荐使用 requirements.txt 安装：

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip
pip install -r requirements.txt
```

如果你用 uv 管理依赖，可以导出 requirements.txt：

```bash
uv export -o requirements.txt
```

2. 执行主程序

```bash
uv run python main.py
```

没有 uv 的等价方式：

```bash
python main.py
```

## 自动更新昨日 Equity（Binance 流水）

新增脚本 `daily_equity_update.py`，会执行以下逻辑：

- 默认读取项目目录下最新的 `Binance-合约交易流水-*.csv`
- 统计昨天的 `REALIZED_PNL`、`FUNDING_FEE`、`COMMISSION`
- 映射为：`profit`、`funding_fee`、`trading_fee`
- 使用前一天（前天）`equity` 作为基准，计算昨天 `equity`
- 自动写回 `data/equity.csv`（若昨天已有记录则覆盖更新）

手动执行：

```bash
uv run python daily_equity_update.py
```

没有 uv 的等价方式：

```bash
python daily_equity_update.py
```

指定日期回填（示例）：

```bash
uv run python daily_equity_update.py --date 2026-04-19
```

没有 uv 的等价方式：

```bash
python daily_equity_update.py --date 2026-04-19
```

从指定日期开始重算（示例，重算 2026-05-01 至 2026-05-16）：

```bash
uv run python daily_equity_update.py --date 2026-05-16 --rebuild-from 2026-05-01
```

没有 uv 的等价方式：

```bash
python daily_equity_update.py --date 2026-05-16 --rebuild-from 2026-05-01
```

指定流水文件（示例）：

```bash
uv run python daily_equity_update.py --binance-csv "Binance-合约交易流水-202604201005(UTC+8).csv"
```

没有 uv 的等价方式：

```bash
python daily_equity_update.py --binance-csv "Binance-合约交易流水-202604201005(UTC+8).csv"
```

## 测试

项目使用 `pytest` 做核心回归测试，覆盖：

- 资金重算（equity）
- 净值与回撤计算（nav）
- 统计指标计算（analytics）
- 数据读取与日期校验（data）

执行测试：

```bash
uv run pytest
```

没有 uv 的等价方式：

```bash
pytest
```

## 资金更新公式

```text
equity = last_equity + profit + funding_fee - trading_fee + deposit - withdraw
```

## 风控规则（已实现）

- Level 0（正常）
	- 条件：无回撤、无连续亏损
	- 风险：2%
- Level 1（轻度风险）
	- 触发条件（任意一个）：连亏 2 次 / 回撤 3%
	- 风险：1.5%
- Level 2（中度风险）
	- 触发条件（任意一个）：连亏 3 次 / 回撤 5%
	- 风险：1%
- Level 3（高风险）
	- 触发条件（任意一个）：连亏 5 次 / 回撤 8%
	- 风险：0.5%
- Level 4（极端风险）
	- 触发条件（任意一个）：回撤 10% / 连亏 7 次
	- 风险：停止交易 2 天，结束后以 Level 2 风险恢复（20-30根k线）

执行规则：

- 同时命中多个条件时，取最高等级作为当前风险等级。

风险恢复机制：

- 触发 Level4 后，进入 2 天停交易窗口（含触发当天）
- 停交易窗口结束后，风险等级先恢复到 Level2
- 连续 2 次有效盈利交易：风险等级降一级
	- 有效盈利定义：单笔收益率 >= 1%
	- 严格模式：只要出现一次不满足阈值（包含小盈利<1%或亏损），连赢计数清零
- 回撤较上次记录恢复 50%：风险等级降一级
- 创新高（当前回撤归零）：直接恢复到 Level 0
	- 新高定义：基于净值（排除资金流入/流出）的历史最高

主程序会输出当前 Level，并在 data/risk_state.json 持久化风险等级与上次回撤，保证恢复机制可以跨天生效。
