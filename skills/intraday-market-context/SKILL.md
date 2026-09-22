---
name: intraday-market-context
description: Analyze premarket Market Context for Global markets, US equities, Gold, Forex, BTC, ETH, or Crypto. Use for 盘前分析、今日市场背景、美元/利率/风险偏好/波动环境、经济事件风险、跨市场确认、相对强弱和异常背离。 Preserve Codex-led signal routing and explanation; never turn the result into entry timing, technical-pattern analysis, trade signals, price targets, or automated execution.
---

# 日内盘前市场背景

把 Digital Oracle 用作跨资产“市场气象站”。回答：**进入今天的交易前，全球市场正在共同定价什么，哪些关系正在失效？**

## 边界

- 只分析盘前 Market Context，不分析1分钟、5分钟、15分钟或1小时K线形态。
- 不给买卖方向、入场、止损、止盈、目标位或上涨/下跌概率。
- 保留 Codex 的问题理解、信号路由、权重判断、跨市场验证和背离解释。
- 数据脚本只提供事实，不用固定 if/else 代替跨市场推理。

## 固定六模块

1. `Event Risk`：今日中/高影响经济事件、央行决议与讲话。
2. `USD`：DXY 当前值、相对前收和今日变化。
3. `Rates`：US 2Y、US 10Y；黄金额外读取 US 10Y Real Yield。财政部数据是日频慢背景。
4. `Equities`：ES、NQ 的隔夜/今日变化。
5. `Volatility`：VIX 水平和变化，只描述波动环境，不把它等同于涨跌方向。
6. `Target-specific`：目标资产自身表现及少量专属数据。

目标专属数据：

- 美股：核心数据 + 美国事件；必要时才补大型权重股财报。
- 黄金：Gold + US 10Y Real Yield，重点检查美元/收益率逆风下的相对强弱。
- FX：EURUSD、GBPUSD、USDJPY 或 AUDUSD + 两边货币事件。利差接口缺失时明确说明，不猜测。
- Crypto：BTC/ETH + Deribit Funding、Open Interest、Basis。

## 执行流程

1. 识别目标：`global / equities / gold / eurusd / gbpusd / usdjpy / audusd / btc / eth / crypto`。
2. 识别时段：Asia、London 或 New York。未指定时允许脚本自动判断。
3. 运行：

   ```bash
   python scripts/intraday_snapshot.py --target <target> --session <session> --pretty
   ```

4. 先检查 `data_quality`、每项 `market_time`、`fetched_at` 与 `freshness`：
   - `fresh`：可作为当前背景证据。
   - `delayed`：可以参考，但必须说明延迟。
   - `stale/unknown`：不得描述成实时事实；降低结论强度。
   - Provider 失败：报告缺口，不静默改用未授权网页抓取。
5. 执行原项目 Signal Routing：
   - `Relevance`：能否回答当前问题？
   - `Time Match`：是否适合当日盘前？
   - `Information Increment`：是否提供独立增量，而非重复同一风险因子？
6. 按主题聚类：USD、Rates、Risk Appetite、Volatility、Asset Specific。
7. Cross Validation：只有多个相对独立市场表达同一主题时，才提高一致性判断；不要多数投票。
8. Divergence：主动查找常见关系失效。例如 DXY、US2Y 与 Gold 同涨，应解释黄金的相对强势，而非只朗读涨跌。
9. Driver：总结利率重定价、美元变化、Risk-on/off、事件等待、事件后重定价或资产自身因素。信号混乱时明确写“无单一主导因素”。

## 时间语义

- `current`：数据源当前可得值。
- `previous_close`：前一交易日或前一官方观测值。
- `since_previous_close_pct`：相对前收变化，盘前可视为隔夜变化。
- `today_change_pct`：相对当前市场本地日期第一条可用观测的变化。
- 日频利率用 `metadata.change_bps`，不得伪装成实时变动。
- 市场闭市、周末和节假日应保留 stale 状态，不用旧值制造“今日行情”。

## 标准输出

默认使用简洁中文：

```text
今日市场背景
事件风险：高/中/低/数据不可用
美元环境：增强/减弱/中性/不清晰
利率环境：偏鹰重定价/偏鸽重定价/期限分化/稳定/不清晰
风险偏好：改善/减弱/混合
波动环境：压缩/正常/扩张/压力/数据不足
跨市场一致性：高/中/低

市场正在定价：...
关键背离：...
各市场背景：...
今日最大风险：...
数据质量：列出 delayed、stale 和失败项
```

如果调用方要求 `WEB_JSON`，只返回合法 JSON，不要代码围栏，遵守调用方给出的 JSON Schema。所有分类必须附 `evidence`，证据至少包含数据键、变化、市场时间和新鲜度。自然语言追问也要重新读取相关数据，不用上一次报告中的数字冒充当前值。

## 护栏

- 不输出虚假精确概率。
- 不把 DXY、VIX、收益率或任何单一变量机械映射为资产涨跌。
- 不把 Funding/OI/Basis 单独解释为交易方向。
- 不隐藏数据缺失或陈旧。
- 不用新闻观点替代交易与事件数据；补充来源必须说明其性质和时间。
- 结论保持条件化，不使用“必涨、必跌、做多、做空”。
