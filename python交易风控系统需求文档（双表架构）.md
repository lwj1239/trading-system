# Python 交易风控系统需求书（含资金费率 + 双表架构）

---

# 一、项目目标

构建一个 **专业交易风控系统（Python）**，用于：

- 记录交易
- 记录资金变化
- 计算净值曲线
- 计算最大回撤
- 计算统计指标
- 自动风控
- 绘制交易曲线

适用于：

- 手动交易
- 币安合约交易
- 永续合约交易

系统核心目标：

**控制最大回撤 + 提高稳定性 + 量化风险**

---

# 二、系统整体架构

系统采用 **双表架构**：

```
trades 交易记录表

equity 资金变化表
```

模块关系：

```
trades
   ↓
equity
   ↓
nav
   ↓
analytics
   ↓
risk
   ↓
plot
```

---

# 三、交易记录表设计（trades）

交易记录表用于记录每一笔交易

字段设计：

| 字段 | 类型 | 说明 |
|------|------|------|
| date | datetime | 交易时间 |
| symbol | string | 交易品种 |
| side | string | long / short |
| entry | float | 开仓价格 |
| exit | float | 平仓价格 |
| size | float | 仓位大小 |
| profit | float | 交易盈亏 |
| risk | float | 本次交易风险 |
| setup | string | 交易策略 |
| notes | string | 备注 |

示例：

```
date,symbol,side,entry,exit,size,profit,risk,setup,notes
2024-01-01,BTC,long,42000,42500,0.5,200,0.02,breakout,good trade
```

---

# 四、资金记录表设计（equity）

资金记录表用于记录所有资金变化：

包括：

- 交易盈亏
- 资金费率
- 手续费
- 入金
- 出金

字段设计：

| 字段 | 类型 | 说明 |
|------|------|------|
| date | datetime | 时间 |
| equity | float | 当前资金 |
| profit | float | 交易盈亏 |
| funding_fee | float | 资金费率 |
| trading_fee | float | 手续费 |
| deposit | float | 入金 |
| withdraw | float | 出金 |
| note | string | 备注 |

示例：

```
date,equity,profit,funding_fee,trading_fee,deposit,withdraw
2024-01-01,10000,0,0,0,10000,0
2024-01-02,10200,200,-10,-3,0,0
```

---

# 五、资金计算规则

资金更新公式：

```
equity = 
    上一次资金
  + profit
  + funding_fee
  - trading_fee
  + deposit
  - withdraw
```

示例：

```
10000
+ 200
- 10
- 3
=
10187
```

---

# 六、净值计算模块（nav）

净值计算：

```
nav = equity / 初始资金
```

示例：

```
10000 → 1.0
10200 → 1.02
10100 → 1.01
```

输出字段：

```
date
nav
peak
drawdown
```

最大回撤计算：

```
drawdown = (peak - current) / peak
```

---

# 七、统计模块（analytics）

统计指标：

核心指标：

- 最大回撤
- 胜率
- 盈亏比
- Profit Factor
- 期望值
- Sharpe Ratio
- 连续盈利次数
- 连续亏损次数
- 平均收益
- 平均亏损

profit factor：

```
profit factor = 总盈利 / 总亏损
```

期望值：

```
expectancy = 
胜率 × 平均盈利
-
失败率 × 平均亏损
```

---

# 八、风控模块（risk）

输入：

- 净值曲线
- 最大回撤
- 连续盈利
- 连续亏损

基础规则：

```
单笔最大风险 = 2%
```

连续盈利风控：

```
盈利 5%
风险降至 1.5%

盈利 8%
风险降至 1%

盈利 10%
停止交易一天
```

连续亏损风控：

```
连续亏损 3 次
停止交易一天

连续亏损 5 次
停止交易一周
```

回撤风控：

```
回撤 5%
风险减半

回撤 8%
风险 1%

回撤 10%
停止交易
```

输出：

```
当前风险 = 1.2%
```

---

# 九、绘图模块（plot）

绘制图表：

资金曲线

净值曲线

回撤曲线

交易收益分布

使用库：

```
pandas
matplotlib
```

输出：

- equity curve
- nav curve
- drawdown curve

---

# 十、项目目录结构

```
trading_risk_system/

├── data/
│   ├── trades.csv
│   └── equity.csv

├── core/
│   ├── data.py
│   ├── equity.py
│   ├── nav.py
│   ├── analytics.py
│   ├── risk.py
│   └── plot.py

├── main.py

└── requirements.txt
```

---

# 十一、系统执行流程

```
读取 trades

读取 equity

计算资金曲线

计算净值曲线

计算统计指标

计算风险

绘制图表
```

---

# 十二、技术选型

Python库：

```
pandas
numpy
matplotlib
sqlite3
```

---

# 十三、系统能力

系统可以实现：

- 自动计算最大回撤
- 自动计算风险
- 自动绘制净值曲线
- 统计策略表现
- 记录资金费率
- 记录手续费

---

# 十四、最终系统能力

系统将成为：

专业交易风控系统

类似：

- 量化交易系统
- 基金净值系统
- 交易日志系统

---

# 版本

V3.0

新增：

- 资金费率
- 手续费
- 仓位大小
- 专业风控系统架构

设计完成

