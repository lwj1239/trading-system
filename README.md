# Python 交易风控系统

基于双表架构实现的交易风控系统，支持：

- 交易记录管理（trades）
- 资金流水管理（equity，含 funding fee / trading fee / deposit / withdraw）
- 资金曲线与净值回撤计算
- 统计指标（胜率、盈亏比、Profit Factor、Expectancy、Sharpe、连续盈亏）
- 规则化风控输出
- 图表输出（equity/nav/drawdown/profit distribution）

## 项目结构

```text
system/
├── core/
│   ├── data.py
│   ├── equity.py
│   ├── nav.py
│   ├── analytics.py
│   ├── risk.py
│   └── plot.py
├── data/
│   ├── trades.csv
│   ├── equity.csv
│   └── nav.csv
├── output/
│   ├── equity_curve.png
│   ├── nav_curve.png
│   ├── drawdown_curve.png
│   └── profit_distribution.png
└── main.py
```

## 运行

1. 安装依赖（核心计算基于 pandas/numpy，统计扩展支持 scipy）

```bash
uv sync
```

若你是新环境，推荐一并安装常用分析库：

```bash
uv add pandas numpy scipy matplotlib
```

2. 执行主程序

```bash
uv run python main.py
```

首次运行若 `data/trades.csv` 或 `data/equity.csv` 不存在，会自动生成示例数据。

## 资金更新公式

```text
equity = last_equity + profit + funding_fee - trading_fee + deposit - withdraw
```

## 风控规则（已实现）

- 基础单笔风险 2%
- 盈利 5% -> 风险 1.5%
- 盈利 8% -> 风险 1%
- 盈利 10% -> 停止交易一天
- 连续亏损 3 次 -> 停止交易一天
- 连续亏损 5 次 -> 停止交易一周
- 回撤 5% -> 风险减半
- 回撤 8% -> 风险 1%
- 回撤 10% -> 停止交易
