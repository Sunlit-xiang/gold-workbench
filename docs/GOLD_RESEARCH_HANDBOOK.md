# Gold研究员手册：从宏观叙事到可被否定的判断

2026-09-18 · G001.2 · 资产身份 **GC Proxy，不是XAUUSD Spot**。

这份材料的目的，是让研究者学会追问证据、识别时间尺度和审查模型，而不是保证阅读后成为“投资大师”。对黄金真正有用的能力包括知道什么时候不该作方向判断。本次实证的结论正是：**没有发现稳定、可认证的短期预测Edge。**

配套：[通用协议](UNIVERSAL_ASSET_RESEARCH_CONTRACT.md)、[预注册与修正记录](GOLD_EXPERIMENT_PROTOCOL.md)、[运行手册](GOLD_RUNBOOK.md)、[完整Factor Catalog](V2_ASSET_FACTOR_CATALOG.md)。

## 1. 黄金究竟在交易什么

黄金同时有货币属性、资产配置属性、实物消费属性和衍生品交易属性。它没有像股票那样可直接折现的经营现金流，价格由边际持有人愿意付出的价格决定；“没有现金流”不等于没有经济驱动。

```text
黄金价格
├─ 持有黄金的相对机会成本
│  ├─ 实际收益率：持有安全利息资产的替代收益
│  └─ 美元：计价效应、非美元购买力与全球金融条件
├─ 货币与风险保险需求
│  ├─ 通胀与货币可信度
│  ├─ 经济/金融尾部风险
│  └─ 储备、地缘政治及制度风险
├─ 边际资金与交易约束
│  ├─ ETF实物申赎、央行与私人配置
│  ├─ CFTC持仓、保证金及杠杆
│  └─ 期货期限结构、期权风险定价
└─ 价格反馈
   ├─ 趋势、追涨/反转、跨资产风险配置
   └─ 流动性冲击时被迫变现
```

这不是一棵“利率上升→卖黄金”的决策树。相同宏观观察至少有三个问题：消息在公布前被预期了多少？价格在观察前已经反应了多少？该冲击会延续还是反转？本项目用截点前变量预测截点后收益，专门检验最后一个问题。

## 2. 我们在复用什么，而不是闭门造车

| 外部研究 | 真正提供的先验 | 本项目采用 / 不采用 |
|---|---|---|
| [World Gold Council · GRAM](https://www.gold.org/goldhub/tools/gold-return-attribution-model) | 经济扩张、风险不确定性、机会成本、动量等驱动分类；周/月历史归因 | 采用经济家族与残差意识；不把同期回归解释力叫作D5预测准确率，也不冒称复制其专有数据和系数 |
| [Chicago Fed · What Drives Gold Prices?](https://www.chicagofed.org/publications/chicago-fed-letter/2021/464) | 实际利率、通胀预期、悲观预期及长期增长；关系存在时期差异 | 支持机会成本/风险分支；其长周期解释不是本项目1日/5日有效系数 |
| [Erb & Harvey · The Golden Dilemma, NBER](https://www.nber.org/papers/w18706) | 实际金价、购买力与长期均值回归；实际投资期限内通胀对冲并不可靠 | 不将CPI高、金价贵作为机械下周涨跌信号 |
| [Moskowitz / Ooi / Pedersen · Time Series Momentum, AQR](https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum) | 多资产自身过去12个月收益的趋势研究 | 保留252D符号基线；20/60D组合和D1/3/5持有是本项目改造，不能继承原论文绩效 |
| [Baur等 · Investing in Gold—Market Timing or Buy-and-Hold?, SSRN](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=3202658) | 大量择时规则的表面收益对数据窥探和时期变化不稳健 | 固定有限实验集，保存NONE；不搜索到60%为止 |
| [Man Group · GOLD!!](https://www.man.com/insights/road-ahead-gold) | 真实利率、估值与财富配置关系可能阶段性脱离 | 作为结构变化的提醒，不把讨论文章视为可复制D5信号 |
| [Research Affiliates · Gold $5,000?](https://www.researchaffiliates.com/content/dam/ra/publications/pdf/1079-gold-5000.pdf) | 黄金真实估值与通胀叙事的辨析 | 纳入长期估值研究背景；未提取或采用一个有D5 OOS证明的公式 |
| [Robeco · Expected Returns 2026–2030](https://www.robeco.com/files/docm/docu-2025-robeco-5-year-expected-returns-the-stale-renaissance.pdf) | 安全资产与多年配置讨论 | 战略资产配置视角，不把五年预期收益移植到一周模型 |
| [Quantpedia · Cross-Asset Price-Based Regimes for Gold](https://quantpedia.com/cross-asset-price-based-regimes-for-gold/) | 黄金与债券动量的跨资产状态研究 | 作为未来可注册的独立实验；原较长动量/配置期限不证明当前D5有效，未因页面绩效直接纳入 |
| [pysystemtrade](https://github.com/pst-group/pysystemtrade) | 成熟系统中的趋势、风险归一化、forecast组合及数据约束工程 | 借鉴显式数学与职责分层；未复制整套引擎或声称独立复现其收益 |

方法名称也需要准确：rolling z-score、Wilder ATR、OLS slope、Ridge regression、time-series momentum、walk-forward、purged labels、block bootstrap都已有成熟定义；本项目自有假设是输入窗口、合并risk变量、GC报价契约、短期限响应、阈值和这组变量的组合。代码中的名称不是新的金融理论。

这是预测标签研究，不是订单策略回测，未另外制造一个成交/P&L引擎，也未运行或修改LEAN。当前没有值得晋级Verified Backtest的可交易策略候选。

## 3. 第一版为什么是这六个方向研究块

| 研究块 | 可执行定义 | 去重与当前结论 |
|---|---|---|
| Trend | 黄金20D与60D对数收益各自用过去756观察、最少252的均值/样本标准差做Z，平均为一块 | MA、5D动量、slope、persistence只作诊断；该趋势块未证明D5稳定Edge |
| DXY | 5个观测日的对数变化做Z | 与实际利率不同经济维度，但共同回归；加入后未证明稳定优于趋势 |
| Real yield | FRED DFII10 10Y TIPS收益率，5日变化×100转换bp，再做Z | 前瞻系数不强制负号；当前正系数与理论压力相反，不因此改写经济理论 |
| Breakeven | T10YIE 5日bp变化做Z | nominal10仅背景，避免nominal/real/breakeven线性重复；该增量未被支持 |
| Risk | `(Z(5D log VIX)-Z(5D log SPX))/2` | 股市/VIX不再各占完整权重；避险与流动性清算可相反，增量未被支持 |
| COT | 固定088691，Managed Money `(long-short)/OI` 的4周变化，在156周历史内Z；至少104个历史周 | 周二观察保守推迟使用，周数据不伪造每日新样本；未证明加入后存在稳定提升 |

上表的“进入”指进入一个**可运行的研究影子全模型**，不是进入已认可的生产交易模型。所有六块的预测资格仍为research_candidate；没有任何一个因子本轮获得forward_validated称号。保留full shadow是为了继续收集可证伪记录，而非宣称它比简单模型更好。

### 3.1 不进入方向评分的分支

- **Context**：5D/20D/252D Momentum、MA、Slope、Trend Persistence、US2Y、US10Y、曲线、SPX分量、Silver relative、Brent、COT level。部分已能计算，但重复或方向不唯一。
- **Risk**：ATR、Realized Volatility、VIX。波动变大不是黄金自动看涨。
- **Disabled**：实际CPI/PCE/NFP surprise、流动性合成、ETF实物净流、央行储备变化、期限carry、IV/skew、Fed预期差、地缘事件、预测市场。拒绝原因是PIT、逐腿历史、consensus或版本化事件契约缺失，不是已经证明这些因素在经济上不重要。

页面每一片叶都有公式和拒绝原因。Disabled不填零事实；它的方向贡献为0，但原始值为缺失。

## 4. 黄金当前分数是怎样算出来的

每月walk-forward拟合：以截点后结果除以事前波动率得到y，以六个已经标准化的输入作X，使用固定alpha=10的Ridge，含截距。每期最多使用过去756个成熟标签；标签成熟和额外5个观测日gap后才能进入训练。

发布的证据指数不是线性收益预测：

```text
linear_y_hat = intercept + Σ(theta_j × normalized_input_j)
E = 2 × tanh(linear_y_hat / 1.5)
common_scale = E / linear_y_hat             # 极限为4/3
contribution_j = common_scale × theta_j × normalized_input_j
base_contribution = common_scale × intercept
E = base_contribution + Σ(contribution_j)
```

单叶FactorScore=`2*tanh(theta_j*x_j/1.5)`是该叶诊断，不直接相加；最终贡献采用共同缩放以保证严格加总。不能把FactorScore乘任意漂亮权重后声称仍是同一回归。当前不使用旧草案的家族预算，因为本轮已预注册用固定Ridge和明确可加归因作为可检验基线，未按结果搜索预算。

### 4.1 第一条实际冻结记录：一个值得警惕的例子

发出时间2026-09-18 03:47:59 UTC，特征截止2026-09-17，版本`Gold.GCProxy.G001.shadow.045eb7dc35b9`。D5约+0.514，状态偏强但**No Edge**。

| 项 | 冻结贡献（约） |
|---|---:|
| 历史截距 / BASE_RATE | +0.3570 |
| Trend | +0.0330 |
| DXY | -0.0440 |
| Real yield | +0.0773 |
| Breakeven | +0.1218 |
| Risk | -0.0153 |
| COT | -0.0159 |
| 合计 | +0.5139 |

净分的大部分来自近期训练样本的截距，而非六条独立看涨消息。若不显示截距，研究者很容易误读成“宏观因素一致确认上涨”。因此页面把BASE_RATE放在主要驱动列表中。

实际利率5日上升22bp，相对历史均值约0.448bp、标准差9.553bp，Z≈2.256。理论背景压力偏负；但本次回归的**未来D5**系数约+0.0263，于是研究贡献偏正。这不是“实际利率上升利多黄金”的新定律，而是一个可能反映反转、共线性、样本噪声或阶段变化的估计，尚无可靠OOS支持。遇到这种情况应降低信任，不能让AI把正系数编成必然的经济故事。

## 5. 实证结果：有没有比简单模型多知道一些

数据：约5209个GC完整日线、1057期固定类别COT，日历史从2006年开始；留出段特征日起点2025-09-17。下表来自数据库G001.2报告`fb9e7104618ce1f67116b731e1943c8db329d3b8e902192bc9f226d36fc811d3`。

这是重建历史的walk-forward OOS，不是严格历史vintage认证，更不是数年真实forward记录。原G001.1保留；G001.2修复开发期边界和非重叠计数，没有改阈值或搜索参数，holdout不再是新的未见样本。

| Horizon | 完整模型留出期有效n | 发声n / Coverage | 方向命中 | 同发声日20D趋势基线 | 命中增量95%块区间 | 非重叠发声n（保守） |
|---|---:|---:|---:|---:|---|---:|
| H4 | 不支持 | — | — | — | 缺PIT小时数据 | — |
| D1 | 249 | 39 / 15.7% | 33.3% | 38.5% | -36.9至+16.7个百分点 | 34 |
| D3 | 248 | 105 / 42.3% | 28.6% | 30.5% | -18.2至+18.4个百分点 | 39 |
| D5 | 245 | 144 / 58.8% | 41.7% | 38.9% | -19.1至+21.8个百分点 | 35 |

Flat阈值为max(10bp, .25×事前horizon波动)。发出方向后遇到Flat算未命中，因此这不是“只剔除零收益后猜正负”的二分类准确率，不能直接与网上的60%截图比较。所有模型同一有效样本比较；页面另外显示共同可比较日期/全部原始日期，不把暖机和缺失隐藏成100%全调度coverage。

D5方向命中本身的20日块bootstrap区间约28.5%–55.4%；增量区间很宽并跨0。没有证据把41.7%包装为潜在60%，也不能根据区间就断言这个数永远不可能改善。

### 5.1 D5逐族添加

| 模型 | 留出期命中 | Coverage | 解释 |
|---|---:|---:|---|
| 永远Positive | 46.5% | 100% | 上涨基准；不是因子预测能力 |
| 20D趋势符号 | 44.9% | 100% | 最简单的近期走势基线 |
| 252D TSMOM符号 | 46.5% | 100% | 此段结果接近固定偏多，不代表独立信息 |
| 仅Trend Ridge | 44.9% | 56.3% | 单输入加截距已解释许多发声 |
| Trend + DXY + Real | 44.4% | 55.1% | 机会成本未稳定改善 |
| 再加Breakeven | 41.4% | 54.3% | 点估计下降，非因果证明 |
| 再加Risk | 40.9% | 55.9% | 未看到稳定增量 |
| 再加COT：Full | 41.7% | 58.8% | 发声变多，不能单看命中变化 |

不能只凭上述不同coverage点估计排序就认定谁最优。进一步限定双方都发声的日期，full与trend_ridge共134天，方向命中差为0；与opportunity_cost共132天，差也为0。这说明该段新增信息更多改变是否跨过阈值，而不是改变共同发声日的方向。区间[0,0]只描述该组观测到的完全相同结果，不是未来两模型永远相同的保证。

逐因子移除也已保存，并未发现足够稳定、独立的预测贡献；本轮不从所有候选里挑一个点估计最高者当新冠军。多重比较下的这些区间仅作探索性诊断，没有控制家族错误率的“显著发现”。

### 5.2 Regime与失效

初版仅按当时VIX水平≥25标stress，否则ordinary；这是固定描述分组，不是拟合出来的最优阈值。整个历史OOS中，D5全模型ordinary命中约38.1%、stress约38.8%；stress下coverage较高，但没有形成可靠“只在恐慌期信它”的证据。按年也很不稳定，不能选表现好的年份讲故事。

## 6. 目前最弱的地方，不只是模型精度

1. **资产价格契约**：GC=F的连续合约切换尚不能逐腿复现。与GLD日收益差的标准差约0.56%，42天绝对差超过2%；这些差异可能来自时点、代理、费用或换月，不能直接断言都是坏数据，也不能直接删掉。
2. **历史可知性**：FRED graph是今天取得的历史版本，不是ALFRED逐发布vintage。滞后一天减少明显look-ahead，但没有彻底修复修订偏差。
   COT的统一滞后也不能准确复原假期、停摆等延迟发布时期；当前没有逐次实际发布时间档案，因此相关OOS仍属exploratory，不能冠以严格PIT认证。
3. **期限错位**：当前模型是日频、次日后的参考收盘基准；不是纽约08:00的即时盘前模型。短期新消息可能在等待期间已被价格吸收。这是当前可复现能力的代价。
4. **样本依赖**：D5的144个发声并非144次独立实验，保守非重叠约35次，不能据此分裂出许多regime调权。
5. **稀疏慢信息**：COT一周一个信息冲击，不能在日填充后当作五份独立证明；央行储备、ETF流和事件惊喜仍缺合格档案。
6. **截距与共线性**：近年金价漂移可能主导判断；real/nominal/breakeven、risk/VIX/SPX仍要检查联合估计稳定性，而非只讲单因素故事。
7. **结果契约**：当前按真实可得日线序列计horizon，尚无完整GC专属交易日历。大间隙被拒绝，小缺口仍需后续对照交易所日历解决。

## 7. XAUUSD Spot值得现在解决吗

值得作为下一笔优先数据投入，但不值得为了“Spot”这个标签匆忙换到不明来源CSV。

| 方案 | 现实条件 | 判断 |
|---|---|---|
| [LBMA / IBA官方benchmark](https://www.lbma.org.uk/prices-and-data/lbma-gold-price) | 基准使用及历史存在许可要求；WGC已说明历史数据因IBA要求受到限制 | 适合明确的AM/PM benchmark契约，不等于24小时可交易spot，也不能免费抓完就公开再分发 |
| [WGC价格数据说明](https://www.gold.org/goldhub/data/gold-prices) | 当前网站不再提供全部原历史LBMA数据，低频均值不能冒充日线 | 不绕过授权或用月均值验证H4 |
| [OANDA v20 candles](https://developer.oanda.com/rest-live-v20/instrument-df/) | 需要账户/API授权和账户可用instrument；字段含complete、价格成分与时间 | 有现实可实施性。先确认XAU_USD在账户可用、报价是dealer/CFD还是目标spot参考、bid/ask、日界和数据许可；本轮不创建账户或索要聊天明文密钥 |
| [Dukascopy官方历史导出](https://www.dukascopy.com/api/data/get/historical-data-export) | 有历史导出入口；需验证XAUUSD具体覆盖、bid/ask、报价尺度、交易时段和允许用途 | 值得做小样本与GC/独立现货对照；未验证的非官方下载器不直接提升为生产主源 |
| Stooq公共CSV | 本轮探测返回HTML而非所需CSV | 当前不可用，未把HTML解析成行情；也没有把项目Stooq兼容层误当独立源 |

优先获得一个许可明确、带完整时间和bid/ask的XAUUSD历史/当前统一源。它能同时改善资产身份、H4输入与Outcome时间，不只增加一片装饰性因子。Spot切换必须新资产/模型族，GC的准确率不继承过去。

## 8. 如何像研究员一样阅读国际信息

遇到一条“美国CPI高于预期”的新闻，依次检查：

1. **事实**：是首次core MoM、headline YoY还是修订值？来源什么时候发布？consensus是否在公布前已存档？
2. **传导**：这次意外主要改变实际利率、通胀补偿、美元还是风险偏好？名义收益率上升不能直接等同实际收益率上升。
3. **已发生反应**：Gold、DXY和rates在同一时间窗口的实际变化是什么？不同收盘时点的反向变化不是证据。
4. **未来假设**：需要假设持续重定价、反转还是风险溢价增加？“已经下跌”本身不证明“还会下跌”。
5. **反证**：如果实际利率上升而黄金更强，是否有资金流、非美元需求、储备调整或强趋势在抵消？若没有数据就写unknown，不临场发明故事。
6. **期限**：当天4小时、下个交易日和一周可以有不同结果。当前H4无认证数据，不能替它下结论。
7. **历史纪律**：找到符合事前定义的历史事件集合，保留失败例和Flat，比较简单基线后再决定是否值得信。

遇到央行买金、ETF流入或地缘事件也走同样步骤；重要不是把所有消息都解释为看涨，而是区分边际新信息与重复确认。成熟判断的一个表现，是能够明确说“我理解这些背景，但它们还没有给我可靠方向优势”。

## 9. 下一项最值得研究什么

**先解决可审计的XAUUSD价格与PIT对齐，再做一个单一新增实验。** 若数据契约通过，优先比较固定cohort的Gold–real yield–DXY响应在更短时间对齐下是否改善；不是先增加十个新指标。随后才值得投入官方ETF实物持仓/申赎档案，检验它是否提供区别于趋势的边际需求信息。

同时继续运行现有GC影子模型，以真实first_seen建立未来可用的证据库。每日计算和每月描述报告可以持续；任何公式、系数或源切换必须新版本。此次没有一个候选被认证为交易优势，是一个有价值且可重现的研究结果。
