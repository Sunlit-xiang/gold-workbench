# Digital Oracle V2 — 四资产因子树与叶节点目录

Draft 1.0 · 2026-09-17。与[主规格](V2_FACTOR_MODEL_SPECIFICATION.md)共同阅读。树是可展开的研究目录，底层是连续特征、分组预算和统计模型，不是if/else决策树。每个ID对应一个可追溯叶子；只有它满足数据与验证条件时才启用。

目录中的状态是设计状态，不表示已实现：

- `A+ / A-`：弱经济方向先验，预测theta初始 +.25 / -.25；Context Score可用±B(s)，预测分用B(theta×s)。标的/历史不合格时仍须禁用。
- `R`：关系需要估计，theta初始0；先采集和展示，不能以经验偷填一个方向。
- `C`：背景/同步解释，方向权重0；有Context Score，不承诺未来方向。
- `K`：风险或数据门控，方向权重0；Risk Score不加到E。
- `A→R`：弱先验的候选，只有主规格指定的初版小核心启用；其余保持0直到发布新版本。

H=H4、1=D1、3=D3、5=D5。`C(H)`表示4H只能作慢背景。适用期限不等于该期限已启用。每一行的分数、beta/theta、预算alpha与Q都遵循主规格第4、6节，未启用贡献确定为0、分数保留null或context值，不是“中性事实”。

## A. 数据源注册表：所有叶子的数据终点

“可回填”仅表示接口/数据类型存在，不代表本项目已拥有清洗后的PIT历史。截止本轮，没有做多年数据下载或估计。

| Source ID | 明确来源/标识/字段 | 发布频率与可用性 | 现有基础 / 增量与限制 |
|---|---|---|---|
| PX | YahooPriceProvider：`DX-Y.NYB`,`EURUSD=X`,`GC=F`,`BTC-USD`及下列交叉符号；OHLC与bar timestamp | 日/周/月历史；MarketCore快照含市场时间 | 现有；历史Provider目前把日期截成YYYY-MM-DD，须补时区/发布时间。小时历史尚未封装 |
| SPOT_GOLD | 待签订的数据契约：XAUUSD、USD/oz、midpoint/历史bid-ask、明确venue与时区 | 目标为至少分钟报价及多年日/小时历史 | 当前无。不得写成已接入；在源确定前Gold现货模型全树为blocked，GCProxy单独研究 |
| USY | USTreasuryProvider nominal curve字段2Y/10Y；real curve字段10Y，按年份CSV批次 | 美国业务日日频，按正式发布日期可用 | 现有；必须归一日期后排序、多年回填，不能依赖CSV第一行就是最新 |
| FRED | `https://api.stlouisfed.org/fred/series/observations`：DFII10、DGS2、DGS10、T10YIE、BAMLH0A0HYM2、DTWEXBGS | 日频；series metadata、release与vintage分别保存 | 待新增Provider、注册Key；DFII10和Treasury real只择一主源，不独立计分 |
| USPOL | FRED DFEDTARL/DFEDTARU目标区间、纽约联储SOFR、Fed正式决定 | 日频/事件驱动 | 待接入；policy midpoint=(upper+lower)/2；SOFR是隔夜融资，不等于预期路径 |
| ECBPOL | ECB SDMX `FM.D.U2.EUR.4F.KR.DFR.LEV`存款利率；ECB正式决定 | 变化日/日频持有，按发布时间 | 本轮公共API验证200；本项目未封装，不能把日频沿用值当每日新消息 |
| EUBOND | ECB `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y`和同stem的`SR_10Y`，AAA欧元区spot curve | TARGET业务日；正式更新时间日历 | 2Y本轮验证200；10Y须接入时验证元数据。不是Bund、OIS，也不同于US par，利差是代理 |
| USMAC | FRED/BLS/BEA：INDPRO、CPIAUCSL、CPILFESL、PCEPILFE、PAYEMS、UNRATE、ICSA | 工业产出/CPI/PCE/就业月频；claims周频 | 待接入PIT；首次发布值与修订值分存，指数/百分比/千人不得混 |
| EUMAC | Eurostat API `.../statistics/1.0/data/sts_inpr_m`，geo=EA20、nace_r2=B-D、s_adj=SCA、freq=M；HICP `prc_hicp_midx` geo=EA20、coicop=CP00、freq=M | 月频；以Eurostat发布表及vintage可用时点为准 | 待接入；unit指数基期由接口code list唯一选择并冻结，元数据变化/EA20缺失则blocked，不能自动换辖区或基期拼接 |
| USLIQ | FRED WALCL（百万USD）、WDTGAL（百万USD）、RRPONTSYD（十亿USD） | WALCL/TGA周频、RRP日频；各自发布时点 | 待接入；按共同已知周截面计算NET_LIQ，不事后回填“同周后来才知道”的值 |
| EULIQ | FRED `ECBASSETSW`（百万EUR）转载ECB周资产负债表 | 周频、存在发布滞后与修订 | 待接入；做变化比例后与US比较，不直接减EUR和USD金额 |
| XEQ | Yahoo `^GSPC`,`^NDX`日历史；盘前快照`ES=F`,`NQ=F` | 现货指数日频，期货盘前延迟报价 | 现有通用能力；现货/期货分ID。H4需要同合约可重建历史，不能日线与期货混训练 |
| XVOL | Yahoo `^VIX`；FRED `VIXCLS`可作官方转载日频备份 | VIX市场时间或最新日频 | 现有Yahoo；备份不能增加独立票。VIX与本资产IV含义不同 |
| XCOM | Yahoo `BZ=F` Brent、`SI=F` Silver、`GC=F` Gold | 日频/延迟快照 | 通用Provider可读取；连续期货换月须审计，Brent供给效应不能固定映射所有资产 |
| XEU | Yahoo `^STOXX50E`；FX `EURJPY=X`,`EURGBP=X`,`EURCHF=X` | 日频；小时需补 | 通用接口可请求、具体覆盖尚未实测。国家风险与货币暴露不等价 |
| COT_G | CFTC `72hh-3qpy` Disaggregated Futures Only；COMEX Gold指定contract code与Managed Money long/short/OI | 通常周五公布周二持仓 | 现有；本轮确认dataset类别。必须固定contract code，不能每天按最高OI选另一个市场 |
| COT_F | CFTC Public Reporting TFF Futures Only：EUR、USD Index（若该类实际包含）、CME BTC；Leveraged Funds与Asset Manager分列 | 周频，发布时间与报告日分离 | 待新增正确schema；若USD Index无该报告则另用Legacy非商业类别，另建factor ID/版本，禁止当同一数据。当前商品Provider不能代替 |
| DER_F | Deribit public instrument/summary/orderbook；新增 `get_funding_rate_history`与`get_index_price` | 当前报价；funding历史小时频 | 现有合约、OI、basis_vs_perpetual；未有完整历史落库。funding历史interest_1h不是current_funding |
| DER_O | Deribit option chain +逐合约ticker的bid/ask/IV/greeks/index；新增多到期处理 | 当前链；历史IV/skew要自行归档或有许可历史 | 当前Provider默认最近到期，不能直接声称已有30D constant maturity surface |
| ETF_O | Yahoo YFinanceProvider：GLD、FXE、UUP期权；bid/ask/OI/IV | 当前期权链 | GLD/FXE/UUP都是代理，分别建ID；缺历史surface，只能从现在归档；不得冒称XAUUSD/OTC FX/DXY期权 |
| CG | CoinGecko `simple/price`（bitcoin,ethereum）、`global`（BTC dominance/market cap）、`coins/markets` | 聚合近实时；按源更新时间 | 现有但timestamp字段需扩展；历史dominance并非当前Provider已具备，必须归档 |
| FUND_FLOW | Gold：SPDR Gold Shares官方每日gold tonnes；BTC：单个spot ETF发行人持仓/BTC units/share、shares outstanding | 日频，发布滞后按first_seen | 尚未接入；只做明确发行人/样本，不能把AUM价格上涨当资金净流入；需要point-in-time归档 |
| CAL | 现有TradingEconomics正式API：CalendarId/Date/DateSpan/Actual/Forecast/Previous/LastUpdate；Fed、ECB、BLS、BEA官方日历补schedule | 事件驱动，调度轮询不是发布频率 | TE未配置；需授权。免费官方日历通常无市场consensus；无consensus不能算surprise |
| PM | Polymarket Gamma事件和CLOB book/history；Kalshi指定market/orderbook | 市场报价/按需 | 现有当前查询；市场映射、PIT历史、规则和深度过滤需增加 |
| GEO | 官方政府/央行/运输机构公告形成有来源URL/hash的版本化事件表；研究候选GPR指数需另建历史源契约 | 不定时事件，日/月GPR不能冒充即时消息 | 当前无。初版可以unknown，LLM不得自行编造机器输入；人工录入必须保存entered_at及原文 |

所有待接入源必须记录准确最终URL/series key与元数据hash。EUMAC、COT_F、SPOT_GOLD、FUND_FLOW等存在绑定验收项时，公式已定义但不能执行；不得用不明来源“尽量猜一个数”。这也是树应向研究者暴露的状态。

关于可得历史：[ECB周资产](https://fred.stlouisfed.org/series/ECBASSETSW)、[ECB曲线方法及历史](https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/euro_area_yield_curves/html/index.en.html)、[CFTC报告分类](https://www.cftc.gov/es/node/128971)、[Deribit历史funding](https://docs.deribit.com/api-reference/market-data/public-get_funding_rate_history)。这些支持接口与定义，不证明本项目已取得历史或具有预测力。

## B. 通用叶子调用约定

主规格T模板中的7片叶子在每棵树分别实例化，使用该资产独有价格，不能共享其数值。T族只有momentum、slope、MA三个方向块，alpha分别=.60/.20/.20；ATR、RV、PERSIST的方向alpha=0。

下表补足目录中使用的公式别名；所有 `Z/RZ/P/B` 均按主规格历史窗和warmup计算。每片叶子的 `Current Value → Transform → Score → alpha → Q → Contribution` 都可由这里展开。

| 代码 | 明确计算规则 |
|---|---|
| XRET | 其他资产r_k；k(H,1,3,5)=(4完成小时,1D,5D,20D)；`s=Z(r_k)`。H用小时W1440、其他W756 |
| XVIX | `x=ln(VIX_t/VIX_t-k)`，k同XRET；`s=RZ(x)`；同时level risk=`V(VIX_t)`；两个字段共享一个叶预算 |
| RESID_X | 冻结多元回归 `x=a+b×parent_risk+e`；新时点residual=`x-a-b×parent_risk`，`s=Z(residual)`；训练窗252共同日/最低126；H需250不同截点日；缺fit为disabled |
| RELFX | 每日 `x=(r(EURJPY)+r(EURGBP)+r(EURCHF))/3`；各配对按同k，`s=Z(x)`；等权研究篮子，非官方指数 |
| USD_EX_EUR | `x=(r(DXY)+.576×r(EURUSD))/.424`；s=Z(x)；同一同步区间、官方权重不变时；去除DXY中EUR机械项的研究代理 |
| POLICY_DIFF | `x=ECB_DFR-(DFEDTARU+DFEDTARL)/2`；level=`L(x)`，change=`Z(100×delta20D(x))`；反向USD取负；方向先验仍须区分水平与意外变化 |
| Y2_RESID | `x=bp_k(US2Y)-b×bp_k(US10Y)`；b在已完成共同窗拟合；s=Z(x)；用来拆期限成分，不多计绝对利率 |
| LIQ_DIFF | `x=change4W(ECB_assets)/abs(lag4W_ECB)-change4W(Fed_assets)/abs(lag4W_Fed)`；s=RZ156(x)；正=ECB扩表相对更快 |
| FLOW | Gold: `x=(tonnes_t-tonnes_t-5D)/tonnes_t-5D`；BTC ETF: `x=sum_i(delta5D(shares_i)×BTC_per_share_i,lag)/sum_i(BTC_holdings_i,lag)`，固定发行人样本；s=RZ756(x) |
| PM_FED | 完整互斥穷尽政策区间合约，非负mid标准化为sum=1只是报价处理；`expected_rate=sum(mid_norm×rate_midpoint)`；x=delta24h(expected_rate)×100bp/pp；s=RZ历史 | 
| TECH_RESID | `x=r_asset,k - fitted_beta'×cross_moves_k`，s=Z(x)；为资产相对强弱C，不在技术趋势和跨资产同时重复贡献 |

PM_FED须所有区间齐全且对应同一会议、合约口径相同；报价和sum偏离1超过.05则不计算，不能擅自补缺失概率。会期更换要按“距会议天数”匹配/独立版本，不把换合约跳变当新消息。

初始实际方向小核心只含T、下文明确列出的M中A节点；X/P/E均先theta=0，生成潜在特征等待验证。这样可以比较一个真实可复现基线，而不是让未验证节点在启动时集体投票。候选预算完整保留，V1方向判断通常谨慎并可能长期No Edge。

## C. USD / DXY 因子树

```text
USD.DXY
├─ 技术状态
│  ├─ U.MOM5 / U.MOM20 → PX.DXY → T.MOM → Z → B(theta×s)
│  ├─ U.SLOPE → PX.DXY → T.SLOPE
│  ├─ U.MA → PX.DXY → T.MA
│  ├─ U.ATR → PX.DXY → T.ATR → Risk
│  ├─ U.RV → PX.DXY → T.RV → Risk
│  └─ U.PERSIST → PX.DXY → T.PERSIST → trend gate
├─ 美国与外国政策、实际利率、增长与流动性
│  ├─ U.FED → USPOL → 政策水平/变化
│  ├─ U.Y2 → USY.2Y → RATE
│  ├─ U.Y10 → USY.10Y → RATE
│  ├─ U.RY → USY.Real10Y → RATE
│  ├─ U.CURVE → USY.10Y/2Y → CURVE
│  ├─ U.REL2 → USY.2Y + EUBOND.2Y → -SPREAD
│  ├─ U.POLDIFF → USPOL + ECBPOL → -POLICY_DIFF
│  ├─ U.GROWTH → USMAC + EUMAC → -REL_GROWTH
│  ├─ U.INFL → USMAC.CPILFESL → MACRO_ACCEL
│  └─ U.LIQ → USLIQ → NET_LIQ
├─ 跨资产与避险
│  ├─ U.SPX → XEQ.SP500 → XRET
│  ├─ U.NDX → XEQ.Nasdaq/SP500 → RESID_X
│  ├─ U.VIX → XVOL → XVIX
│  ├─ U.CREDIT → FRED.HY_OAS → Z(delta)
│  ├─ U.BRENT → XCOM.Brent → XRET
│  ├─ U.GOLD → Gold price → XRET
│  └─ U.BROAD → FRED.DTWEXBGS → XRET / broad-vs-DXY差异
├─ 仓位与波动定价
│  ├─ U.COT → COT_F.USD → COT level/flow
│  ├─ U.IV → ETF_O.UUP → IV30
│  └─ U.SKEW → ETF_O.UUP → Skew30
└─ 事件与信息
   ├─ U.FOMC → CAL/Fed → 决议surprise + 临近风险
   ├─ U.CPI → CAL/BLS → 核心CPI环比surprise
   ├─ U.PCE → CAL/BEA → 核心PCE环比surprise
   ├─ U.NFP → CAL/BLS → 首次NFP surprise
   ├─ U.FOREIGN → CAL/ECB → 外国央行事件风险
   ├─ U.GEO → GEO → 事件风险
   └─ U.PM → PM → PM_FED / PM变化
```

U.MOM5、U.MOM20、U.SLOPE、U.MA、U.ATR、U.RV、U.PERSIST完整定义见主规格T表：来源PX `DX-Y.NYB`、日/小时频、H/1/3/5，分别实例化，不引用EUR价格。以下列出其他每一个叶子：

| ID | 源、频率 | Horizon | Transform与Context Score | 初始预测角色 / alpha | 经济含义、依赖或非线性 |
|---|---|---|---|---|---|
| U.FED | USPOL，决定/日 | C全期限 | `LEVEL(policy_mid)`及bp变化；B(L) | C / 0 | 政策水平已被定价，不等于政策意外 |
| U.Y2 | USY，日 | 1/3/5；C(H) | RATE；+B(s) | A+ / M的.40 | 短端重定价可能支持美元；与REL2同簇 |
| U.Y10 | USY，日 | 全期限C | RATE；B(s)原始冲击 | C / 0 | 增长、通胀、期限溢价混合，无固定方向 |
| U.RY | USY Real10Y，日 | 1/3/5；C(H) | RATE；+B(s)理论压力 | R / 0 | 实际收益吸引力，可能被利差解释，需联合回归 |
| U.CURVE | USY，日 | 3/5；其他C | CURVE；B(s) | C / 0 | 曲线形变不是美元自动方向 |
| U.REL2 | USY+EUBOND，日 | 1/3/5；C(H) | -SPREAD；B(s) | A+对US-EU变化 / M的.60 | DXY以欧元权重最大，此为部分篮子代理；非纯OIS差 |
| U.POLDIFF | USPOL+ECBPOL，事件/日 | 3/5；其他C | -POLICY_DIFF；B(level/change) | C / 0 | 已知政策差与市场预期差分开 |
| U.GROWTH | USMAC+EUMAC，月 | 3/5 | -REL_GROWTH；B(s) | R / 0 | 美国相对增长；月度发布样本少 |
| U.INFL | USMAC.CPILFESL，月 | 3/5 | MACRO_ACCEL；B(s) | C / 0 | 通胀引发政策与购买力两条相反作用 |
| U.LIQ | USLIQ，周/日合成 | 3/5 | NET_LIQ；B(s) | R / 0 | 美元供给/融资压力方向需控制风险状态 |
| U.SPX | XEQ，日或H历史 | H/1/3/5 | XRET；B(s) | R / X预留.35 | 避险美元与美国增长优势可能方向相反 |
| U.NDX | XEQ，日/H | H/1/3/5 | RESID_X(NDX对SPX)；B(s) | C / 0 | 不把两个高度相关股指当独立票 |
| U.VIX | XVOL，报价/日 | H/1/3/5 | XVIX；B(s)及Risk | R / X预留.35 | 风险厌恶可能支持美元，也可能是美国自身冲击 |
| U.CREDIT | FRED.HY_OAS，日 | 1/3/5 | `Z(delta_k(OAS bp))`；B(s) | R / X预留.30 | 美元融资紧张的代理；与VIX共享risk block |
| U.BRENT | XCOM，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 供给/需求冲击不能简单相同方向 |
| U.GOLD | SPOT_GOLD或独立GCProxy，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 检查美元与避险资产同涨背离 |
| U.BROAD | FRED.DTWEXBGS，日 | 1/3/5 | XRET；`rBroad-rDXY`另显示 | C / 0 | 验证DXY强势是否局限于篮子，不能重复美元趋势 |
| U.COT | COT_F固定类别，周 | 3/5；C(1,H) | COT；B(flow)、level | R / P预留1.00 | USD报告类型需绑定；无法绑定不拿反向EUR替代 |
| U.IV | ETF_O.UUP，快照/归档 | 全期限 | IV30，V(IV) | K / 0 | UUP期权代理风险，流动性不足则disabled |
| U.SKEW | ETF_O.UUP，快照/归档 | 1/3/5 | SKEW；B(s) | C / 0 | 代理期权与DXY结构不同，待独立研究 |
| U.FOMC | CAL+USPOL，事件 | H/1/3/5 | 政策SURPRISE、EVT分别保存 | R / E预留.40 | 高于预期偏鹰方向仅是假设，路径信息可能相反 |
| U.CPI | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE(core MoM)；+B(s)先验展示 | R / E预留.20 | 消息与利率反应同簇，不能重复加权 |
| U.PCE | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE(core MoM)；+B(s) | R / E预留.20 | 对已知CPI信息可能增量低 |
| U.NFP | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE(first payroll change)；+B(s) | R / E预留.20 | 同时保留前月修订，初版不另加方向 |
| U.FOREIGN | CAL+ECBPOL，事件 | 全期限 | EVT；Risk | K / 0 | 外国央行意外影响美元相对吸引力，不能只盯Fed |
| U.GEO | GEO，事件 | 全期限 | GEO；Risk | K / 0 | 冲击发生地区决定美元反应，无固定符号 |
| U.PM | PM，按需 | 全期限C | PM_FED或PM；B(s) | C / 0 | 在不重复利率反应前提下才可晋级R |

USD初版M只启用U.Y2(.40)与U.REL2(.60)，它们共用rates经济簇；联合拟合后可能删掉U.Y2。不能说两者同向就是两份独立确认。未来加入日本/英国政策及利率必须另注册数据源、再检验是否改善DXY；当前美元篮子覆盖仍有缺口，页面明确展示。

## D. EURUSD 因子树

```text
FX.EURUSD.SPOT
├─ 自身技术状态
│  ├─ E.MOM5 / E.MOM20 → EURUSD自身价格 → T
│  ├─ E.SLOPE / E.MA → EURUSD自身价格 → T
│  └─ E.ATR / E.RV / E.PERSIST → 风险与趋势质量
├─ 美元侧、欧元侧与相对差异
│  ├─ E.FED → USPOL → 美国政策状态
│  ├─ E.ECB → ECBPOL → 欧洲政策状态
│  ├─ E.US2 / E.US10 → USY → RATE
│  ├─ E.EU2 / E.EU10 → EUBOND → RATE
│  ├─ E.SPREAD2 → EU2-US2 → SPREAD
│  ├─ E.CURVEDIFF → (EU10-EU2)-(US10-US2) → 曲线差变化
│  ├─ E.POLDIFF → ECB-Fed → POLICY_DIFF
│  ├─ E.GROWTH → 欧洲IP/美国IP → REL_GROWTH
│  ├─ E.INFLDIFF → 欧元区HICP/美国CPI → 各自标准化后差异
│  └─ E.LIQDIFF → ECB/Fed资产变化比例差 → LIQ_DIFF
├─ 跨资产与独立货币强弱
│  ├─ E.USDX → DXY剔除EUR机械项 → USD_EX_EUR
│  ├─ E.EURX → EURJPY/EURGBP/EURCHF → RELFX
│  ├─ E.EQREL → EuroStoxx50/SP500 → 本币股指相对收益
│  ├─ E.VIX → XVOL → XVIX
│  ├─ E.BRENT → XCOM → XRET
│  └─ E.NDX → NDX相对SPX → RESID_X
├─ 仓位与期权
│  ├─ E.COT → COT_F.EUR → 净头寸占OI/变化
│  ├─ E.IV → ETF_O.FXE → 代理IV30
│  └─ E.SKEW → ETF_O.FXE → 代理Skew30
└─ 双侧事件
   ├─ E.FOMC / E.ECB_EVENT → 央行实际-预期
   ├─ E.US_CPI / E.US_NFP → 美国surprise
   ├─ E.EU_HICP → 欧元区surprise
   ├─ E.CALENDAR → 双侧EVT
   ├─ E.GEO → 欧洲/美国/全球事件标签
   └─ E.PM → 相关政策PM变化
```

E.MOM5、E.MOM20、E.SLOPE、E.MA、E.ATR、E.RV、E.PERSIST采用T：Source=PX `EURUSD=X`，日/小时频，H/1/3/5。正向永远表示EUR升值。EURUSD不能只被写成反向DXY。

| ID | 源、频率 | Horizon | Transform与Context Score | 初始预测角色 / alpha | 经济含义和限制 |
|---|---|---|---|---|---|
| E.FED | USPOL，日/决定 | 全期限C | LEVEL(policy_mid)；B(L) | C / 0 | 美国侧政策状态 |
| E.ECB | ECBPOL，变化日 | 全期限C | LEVEL(DFR)；B(L) | C / 0 | 欧洲侧政策状态；DFR与Fed midpoint口径记录 |
| E.US2 | USY.2Y，日 | 全期限C | RATE；-B(s)理论压力 | C / 0 | 展开SPREAD2的美国输入，不重复贡献 |
| E.US10 | USY.10Y，日 | 全期限C | RATE；B(s)原始变化 | C / 0 | 增长/期限溢价混合 |
| E.EU2 | EUBOND.2Y，日 | 全期限C | RATE；+B(s)理论压力 | C / 0 | AAA零息代理，不是德国收益率 |
| E.EU10 | EUBOND.10Y，日 | 全期限C | RATE；B(s) | C / 0 | 同上 |
| E.SPREAD2 | EUBOND+USY，日 | 1/3/5；C(H) | SPREAD；+B(s) | A+ / M的1.00 | 欧美相对利率变化，初版集中一个可解释利差块 |
| E.CURVEDIFF | 两侧2/10Y，日 | 3/5 | `x=100×delta_k[(EU10-EU2)-(US10-US2)]`；s=Z(x) | R / 0 | 曲线预期与期限溢价，需控制SPREAD2 |
| E.POLDIFF | USPOL+ECBPOL，事件/日 | 3/5 | POLICY_DIFF；B(level/change) | C / 0 | 已公布政策差，不代替未来路径 |
| E.GROWTH | USMAC+EUMAC，月 | 3/5 | REL_GROWTH；+B(s)理论 | R / 0 | 双侧可比工业产出；不能拿美国GDP对欧洲PMI直接减 |
| E.INFLDIFF | CPIAUCSL+EU HICP，月 | 3/5 | 两侧MACRO_ACCEL分别Z；`s=(Z_EU-Z_US)/sqrt(2)`；B(s) | R / 0 | 口径有差异；政策利好与实际收入压力竞争 |
| E.LIQDIFF | EULIQ+WALCL，周 | 3/5 | LIQ_DIFF；-B(s)弱理论展示 | R / 0 | 欧洲扩表更快不必然欧元下跌；状态依赖 |
| E.USDX | PX.DXY/EURUSD，同步日/H | H/1/3/5 | USD_EX_EUR；-B(s) | R / X预留.40 | 去EUR机械重复；异步报价不计算残项 |
| E.EURX | XEU三货币对，同步日/H | H/1/3/5 | RELFX；+B(s) | R / X预留.30 | 观察欧洲自身强弱，但仍与EURUSD共享EUR因子 |
| E.EQREL | XEU+XEQ，日/H | 1/3/5；H待历史 | `s=Z(r_k(STOXX50)-r_k(SPX))`；B(s) | R / X预留.15 | 两个本币指数相对风险偏好，不能使用美元计价EU ETF制造汇率循环 |
| E.VIX | XVOL，日/报价 | H/1/3/5 | XVIX；Risk及B(s) | R / X预留.15 | 风险状态，方向可能随美国/欧洲冲击变化 |
| E.BRENT | XCOM，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 能源进口压力假设与全球需求繁荣可能相反 |
| E.NDX | XEQ，日/H | H/1/3/5 | RESID_X；B(s) | C / 0 | 只作美国科技相对风险诊断 |
| E.COT | COT_F EUR Leveraged Funds，周 | 3/5；C(1,H) | COT flow与level；B(flow) | R / P预留1.00 | 欧元净多拥挤不一定反转；报告发布日期生效 |
| E.IV | ETF_O.FXE，快照/归档 | 全期限 | IV30；V(IV) | K / 0 | ETF代理而非OTC FX IV；门槛不满足时空缺 |
| E.SKEW | ETF_O.FXE，快照/归档 | 1/3/5 | SKEW；B(s) | C / 0 | 缺OTC risk reversal历史，先不进入方向 |
| E.FOMC | CAL+USPOL，事件 | H/1/3/5 | 政策SURPRISE；-B(s)先验展示 | R / E预留.25 | 美国政策高于预期可能压EUR，需验证信息效应 |
| E.ECB_EVENT | CAL+ECBPOL，事件 | H/1/3/5 | 政策SURPRISE；+B(s) | R / E预留.25 | 欧洲政策预期必须单独取得 |
| E.US_CPI | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE核心环比；-B(s) | R / E预留.20 | 同美国利率变化去重 |
| E.US_NFP | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE首发新增就业；-B(s) | R / E预留.10 | 避免将修订后数据放进旧账本 |
| E.EU_HICP | CAL+EUMAC，月事件 | H/1/3/5 | SURPRISE HICP flash YoY；+B(s) | R / E预留.20 | 不能将flash与final视为同类新冲击 |
| E.CALENDAR | CAL双侧，事件 | 全期限 | EVT；Risk | K / 0 | 欧洲与美国都必须有coverage，缺一侧显示缺口 |
| E.GEO | GEO，事件 | 全期限 | GEO并按region列出；Risk | K / 0 | 初版不把“欧洲新闻”自动判欧元利空 |
| E.PM | PM，按需 | 全期限C | PM变化/各自政策市场；B(s) | C / 0 | 事件与两侧利率路径未必一一对应 |

EURUSD初始M预算集中SPREAD2是参数节约，并非说欧洲其他因素不重要。若欧洲数据缺失，E.GROWTH等保持missing；不能用美国数据替代后把树称为双侧完整。真实市场路径研究若有SOFR/€STR OIS，应注册独立同期限forward spread替换代理；本次未假设有免费OIS历史。

## E. Gold / XAUUSD 因子树

```text
Gold（XAUUSD目标；当前GCProxy必须单独标识）
├─ 技术状态
│  ├─ G.MOM5 / G.MOM20 → Gold自身价格 → T
│  ├─ G.SLOPE / G.MA → Gold自身价格 → T
│  └─ G.ATR / G.RV / G.PERSIST → 波动与趋势质量
├─ 利率、美元与通胀
│  ├─ G.DXY → PX.DXY → XRET
│  ├─ G.US2 → USY.2Y → RATE
│  ├─ G.US10 → USY.10Y → RATE
│  ├─ G.RY → USY.Real10Y → RATE + 预测敏感度
│  ├─ G.BEI → 同日US10-Real10 → 盈亏平衡变化
│  ├─ G.CURVE → USY.10Y/2Y → CURVE
│  ├─ G.INFL → USMAC.CPILFESL → MACRO_ACCEL
│  └─ G.LIQ → USLIQ → NET_LIQ
├─ 跨资产与避险需求
│  ├─ G.SPX → XEQ.SP500 → XRET
│  ├─ G.NDX → XEQ.Nasdaq/SP500 → RESID_X
│  ├─ G.VIX → XVOL → XVIX
│  ├─ G.CREDIT → FRED.HY_OAS → 信用压力变化
│  ├─ G.BRENT → XCOM.Brent → XRET
│  ├─ G.BTC → PX.BTC → XRET
│  ├─ G.SILVER → Gold/Silver → 相对收益
│  └─ G.RESILIENCE → Gold实际变化减利率/美元解释部分 → 残差
├─ 持仓、需求与衍生品
│  ├─ G.COT → COT_G → Managed Money净头寸/OI
│  ├─ G.ETF → SPDR官方gold tonnes → FLOW
│  ├─ G.IV → ETF_O.GLD → IV30代理
│  └─ G.SKEW → ETF_O.GLD → Skew30代理
└─ 事件与信息
   ├─ G.FOMC → Fed决定/预期 → 政策surprise与EVT
   ├─ G.CPI / G.PCE / G.NFP → 首次发布/冻结consensus → SURPRISE
   ├─ G.CALENDAR → CAL → EVT
   ├─ G.GEO → GEO → 风险
   └─ G.PM → PM → 有流动性的相关事件变化
```

G.MOM5、G.MOM20、G.SLOPE、G.MA、G.ATR、G.RV、G.PERSIST采用T；Source=SPOT_GOLD或另一个模型族PX `GC=F`，日/小时频，H/1/3/5。不能在一个窗口里拼现货与换月期货。

| ID | 源、频率 | Horizon | Transform与Context Score | 初始预测角色 / alpha | 经济含义、重复与状态依赖 |
|---|---|---|---|---|---|
| G.DXY | PX.DXY，日/H | H/1/3/5 | XRET；-B(s) | A- / M的.40 | 美元计价与金融条件；不是恒定反向关系 |
| G.US2 | USY，日 | 全期限C | RATE；-B(s)理论 | C / 0 | 政策压力辅助，避免叠加RY重复 |
| G.US10 | USY，日 | 全期限C | RATE；B(s)冲击 | C / 0 | nominal包含real与breakeven |
| G.RY | USY real10Y主源，日 | 1/3/5；C(H) | RATE k=1/5/20；-B(s) | A- / M的.60 | 无息资产机会成本；允许预测theta收缩0，非线性/压力交互候选 |
| G.BEI | 同日USY nominal10-real10，日 | 3/5 | `Z(bp_k(nominal-real))`；+B(s)理论 | C / 0 | 市场breakeven含流动性/风险溢价，不是纯通胀预期 |
| G.CURVE | USY，日 | 3/5；其他C | CURVE；B(s) | C / 0 | 曲线变化不直接等于黄金方向 |
| G.INFL | USMAC核心CPI，月 | 3/5 | MACRO_ACCEL；B(s) | C / 0 | 通胀对保值需求与加息预期的作用竞争 |
| G.LIQ | USLIQ，周合成 | 3/5 | NET_LIQ；B(s) | R / 0 | 流动性宽松假设，短期危机可能出现抛售黄金 |
| G.SPX | XEQ，日/H | H/1/3/5 | XRET；B(s) | R / X预留.30 | 共同风险或避险，符号不预设 |
| G.NDX | XEQ，日/H | H/1/3/5 | RESID_X；B(s) | C / 0 | 科技暴露与SPX去重 |
| G.VIX | XVOL，日/报价 | H/1/3/5 | XVIX；B(s)/Risk | R / X预留.40 | 避险需求与现金挤兑竞争；stress交互候选 |
| G.CREDIT | FRED.HY_OAS，日 | 1/3/5 | `Z(delta_k(OAS bp))`；B(s) | R / X预留.30 | 信用压力与VIX同risk簇，不加独立票 |
| G.BRENT | XCOM，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 通胀/供给冲击背景，避免固定正相关 |
| G.BTC | PX.BTC，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 检查风险资产共同性，“数字黄金”不能作为系数依据 |
| G.SILVER | XCOM银+Gold价格，日/H | 1/3/5 | `Z(rGold_k-rSilver_k)`；B(s) | C / 0 | 贵金属相对表现，不把Gold自身收益再算一次预测证据 |
| G.RESILIENCE | Gold+RY+DXY，日 | 1/3/5 | TECH_RESID；B(s) | C / 0 | 美元/利率逆风下的相对强弱；包含目标自身已发生收益 |
| G.COT | COT_G，周 | 3/5；C(1,H) | COT；B(flow)及level | R / P预留.60 | Managed Money仓位不是明确买盘；极端持仓符号不固定 |
| G.ETF | FUND_FLOW官方Gold tonnes，日 | 1/3/5 | FLOW；+B(s)理论 | R / P预留.40 | 固定SPDR样本的持有量变化，不等于全球黄金需求 |
| G.IV | ETF_O.GLD，快照/归档 | 全期限 | IV30；V(IV) | K / 0 | 代理隐含风险，无上涨方向 |
| G.SKEW | ETF_O.GLD，快照/归档 | 1/3/5 | SKEW；B(s) | C / 0 | 需要surface历史；不能把GLD近到期期权当现货Gold 30D skew |
| G.FOMC | CAL+USPOL，事件 | H/1/3/5 | 政策SURPRISE；-B(s)理论及EVT | R / E预留.40 | 实际利率反应、信息效应共同作用 |
| G.CPI | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE核心CPI MoM；B(s)冲击 | R / E预留.20 | 不预设“高通胀必利多”或“必利空” |
| G.PCE | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE核心PCE MoM；B(s) | R / E预留.20 | CPI之后的信息增量须消融 |
| G.NFP | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE首次新增就业；B(s) | R / E预留.20 | 政策与增长/避险渠道可能对冲 |
| G.CALENDAR | CAL，事件 | 全期限 | EVT；Risk | K / 0 | 未来事件只能提高不确定性，不能假定公布结果 |
| G.GEO | GEO，事件 | 全期限 | GEO；Risk | K / 0 | 没有核实的定量事件输入时显示unknown |
| G.PM | PM，按需 | 全期限C | PM变化；B(s) | C / 0 | 有条件的事件定价，与地缘/Fed节点共用event cluster |

Gold的“完整”是本轮4H…5D候选研究范围内闭合的数据与公式图，不声称穷尽黄金经济学。央行储备购买、珠宝需求、矿产供给对长周期重要，但发布慢、可能修订，暂不进入短期限方向树；需要时作为明确的季度/月度context扩展。不能为了看起来完整给它们日内权重。

## F. BTC 因子树

```text
CRYPTO.BTCUSD.REFERENCE
├─ 技术状态
│  ├─ B.MOM5 / B.MOM20 → BTCUSD价格 → T
│  ├─ B.SLOPE / B.MA → BTCUSD价格 → T
│  └─ B.ATR / B.RV / B.PERSIST → 风险与趋势质量
├─ 美元、利率与流动性
│  ├─ B.DXY → PX.DXY → XRET
│  ├─ B.US2 → USY.2Y → RATE
│  ├─ B.RY → USY.Real10Y → RATE
│  ├─ B.LIQ → USLIQ → NET_LIQ
│  └─ B.POLICY → USPOL → LEVEL
├─ 跨资产与Crypto广度
│  ├─ B.SPX → XEQ.SP500 → XRET
│  ├─ B.NDX → XEQ.Nasdaq/SP500 → RESID_X
│  ├─ B.VIX → XVOL → XVIX
│  ├─ B.CREDIT → FRED.HY_OAS → 信用压力
│  ├─ B.GOLD → Gold price → XRET
│  ├─ B.ETHREL → CG/PX ETH与BTC → 相对收益
│  └─ B.DOM → CG.global BTC dominance → 占比变化
├─ Crypto衍生品与资金需求
│  ├─ B.FUND → DER_F interest_1h → FUND
│  ├─ B.OI → DER_F OI/index → OI
│  ├─ B.BASIS → DER_F dated future/index → 30D BASIS
│  ├─ B.IV → DER_O → 30D IV
│  ├─ B.SKEW → DER_O → 30D 25delta skew
│  ├─ B.VRP → DER_O + BTC RV → VRP
│  ├─ B.COT → COT_F CME BTC → COT
│  └─ B.ETF → 固定ETF发行人样本 → FLOW
└─ 事件与信息
   ├─ B.FOMC / B.CPI / B.NFP → CAL → SURPRISE
   ├─ B.CALENDAR → CAL → EVT
   ├─ B.CRYPTO_EVENT → SEC/交易所/协议正式事件 → GEO型风险
   ├─ B.GEO → GEO → 风险
   └─ B.PM → Crypto监管等事件PM → 价格变化
```

B.MOM5、B.MOM20、B.SLOPE、B.MA、B.ATR、B.RV、B.PERSIST采用T；Source=PX `BTC-USD`的锁定参考源，日/小时频，H/1/3/5；BTC日频按UTC和365日。周末宏观数据不更新，不因此生成“零变化证明环境稳定”。

| ID | 源、频率 | Horizon | Transform与Context Score | 初始预测角色 / alpha | 经济含义、非线性与数据限制 |
|---|---|---|---|---|---|
| B.DXY | PX.DXY，日/H | H/1/3/5 | XRET；-B(s)理论 | A- / M的.50 | 美元金融条件，Crypto独立行情可能背离 |
| B.US2 | USY，日 | 1/3/5；C(H) | RATE；-B(s)理论 | R / 0 | 政策机会成本，先避免与RY叠加 |
| B.RY | USY real10，日 | 1/3/5；C(H) | RATE；-B(s)理论 | A- / M的.50 | 弱理论先验，历史不稳定可收缩至0 |
| B.LIQ | USLIQ，周 | 3/5 | NET_LIQ；+B(s)理论 | R / 0 | 不是央行资产每加1元就买BTC的因果关系 |
| B.POLICY | USPOL，事件/日 | 全期限C | LEVEL；B(L) | C / 0 | 当前政策状态 |
| B.SPX | XEQ，日/H | H/1/3/5 | XRET；B(s) | R / X预留.40 | 与风险资产联动但不恒定 |
| B.NDX | XEQ，日/H | H/1/3/5 | RESID_X；B(s) | R / X预留.30 | 去SPX共同暴露后科技风险增量 |
| B.VIX | XVOL，日/报价 | H/1/3/5 | XVIX；B(s)/Risk | R / X预留.30 | BTC周末只有最后传统市场观察，须时效门控 |
| B.CREDIT | FRED.HY_OAS，日 | 1/3/5 | `Z(delta_k(OAS bp))`；B(s) | C / 0 | 同risk簇，初期作为压力状态输入 |
| B.GOLD | SPOT_GOLD/独立GCProxy，日/H | H/1/3/5 | XRET；B(s) | C / 0 | 检查BTC是否表现出避险关联，不写固定正向 |
| B.ETHREL | CG/PX ETH和BTC，同步日/H | H/1/3/5 | `s=Z(rETH_k-rBTC_k)`；B(s) | C / 0 | Crypto风险扩散，包含BTC自身项，不重复贡献 |
| B.DOM | CG.global，快照/日归档 | 1/3/5 | `s=RZ(delta_k(BTC_dominance_pp))`；B(s) | C / 0 | 占比上升可能是BTC强或其他币崩，方向不固定 |
| B.FUND | DER_F，小时/24h合成 | H/1/3/5 | FUND；B(s) | R / P预留.30(H,1),.25(3,5) | 正费率既可表示需求也可表示拥挤；候选hinge非线性 |
| B.OI | DER_F inverse BTC-PERPETUAL，报价/小时归档 | H/1/3/5 | OI合约数24h变化；B(s) | R / P预留.30(H,1),.25(3,5) | 新多空同时出现，净方向未知；按合约metadata定单位，不把固定USD面额除价格后误当新增持仓 |
| B.BASIS | DER_F，报价/小时归档 | H/1/3/5 | BASIS；B(s) | R / P预留.25(H,1),.20(3,5) | 杠杆需求、套利约束、借贷成本；高值可能尾部风险 |
| B.IV | DER_O，报价/日归档 | 全期限 | IV；V(IV) | K / 0 | 隐含波动是风险，不是方向 |
| B.SKEW | DER_O，报价/日归档 | H/1/3/5 | SKEW；B(s) | R / P预留.15 | 正skew定义为put-call，不能临时颠倒符号 |
| B.VRP | DER_O+BTC RV，日 | 1/3/5 | VRP；B(s) | C/K / 0 | 过去RV与未来IV比较仅为风险定价背景 |
| B.COT | COT_F CME BTC，周 | 3/5；C(1,H) | COT；B(flow)/level | R / P预留.05(3,5)，H/1为0 | CME leveraged funds做空可能是basis trade对冲，不能直接看空BTC |
| B.ETF | FUND_FLOW，日 | 3/5；C(1,H) | FLOW；B(s) | R / P预留.10(3,5)，H/1为0 | 固定发行人样本的申赎代理，不用AUM变化冒充流量 |
| B.FOMC | CAL+USPOL，事件 | H/1/3/5 | 政策SURPRISE；B(s)冲击 | R / E预留.40 | 金融条件与信息效应需估计 |
| B.CPI | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE核心MoM；B(s) | R / E预留.30 | 与DXY/利率反应同event簇 |
| B.NFP | CAL+USMAC，月事件 | H/1/3/5 | SURPRISE first payroll；B(s) | R / E预留.30 | 强数据可能带来增长支持或政策压力 |
| B.CALENDAR | CAL，事件 | 全期限 | EVT；Risk | K / 0 | 未来发布只影响风险门控 |
| B.CRYPTO_EVENT | GEO契约，SEC/交易所/协议公告 | 全期限 | 主规格GEO式，事件权重：暂停交易/重大安全事件=1、已确认监管决定=.5；Risk | K / 0 | 报道不等于确认，重放时使用当时录入时间；初始无方向 |
| B.GEO | GEO，事件 | 全期限 | GEO；Risk | K / 0 | 和Crypto-specific事件按ID去重 |
| B.PM | PM，按需 | 全期限C | PM；B(s) | C / 0 | 监管事件与资产涨跌合约分开，后者易重复价格趋势 |

BTC的P预算较高表示优先投入数据建设，初版R均为0意味着“尚未知道如何可靠映射方向”。不能为了填满25%的预算就把Funding、OI和Basis都视作多头信号。每个节点获取历史、做联合估计和消融后才有新版本权重。

## G. 每片叶子的权重如何确定，不再隐藏在文字里

1. 每资产7片T叶使用主规格固定块内权重；M初始USD=.40 U.Y2+.60 U.REL2，EUR=1.00 E.SPREAD2，Gold=.60 G.RY+.40 G.DXY，BTC=.50 B.DXY+.50 B.RY。H的日频利率叶按C处理，预留不转移。
2. 表中X/P/E的预留alpha和为1（BTC按期限分配），只是候选manifest的预算。初版theta=0，所有真实激活都需要新版本。未列alpha的R节点为0，新增时须明确从哪一个既有alpha转出，不能把总权重加大。
3. 同一叶的多个期限窗口由h选择，而不是把1D/5D/20D都作为独立票；每个h独立训练theta。主规格技术momentum双窗口是唯一预先定义的组合。
4. C/K节点实际方向alpha=0，显示的Context/Risk分有用途但不会被总分吃进去。比如G.IV改变风险视图和候选门槛，不能给Gold加多头分。
5. alpha、theta和B不能同时任意优化：第一轮固定B/alpha仅估theta；另一个独立试验才能研究预算变化。否则参数不可识别，无法说哪种改变有效。
6. 所有公式中的响应变量是同asset/h的未来标准化收益；没有拿EUR模型系数直接翻号当DXY模型，也没有拿Gold系数复制BTC。

## H. 现在能估什么，必须等待什么

| 关系/因子 | 可用基础 | 现在能支持的工作 | 不能宣称的能力 |
|---|---|---|---|
| 四资产日频技术项 | 现有Yahoo日历史接口 | 回填审计后计算Z/ATR/ER及简单预测基线 | 本轮未回填，不能声称训练完；Gold现货尚无数据契约 |
| Gold–DXY–实际利率、BTC–风险资产 | Yahoo与多年Treasury可请求 | 对齐日频同步beta；回填PIT审计后研究滞后预测theta | 日线不能验证08:00→12:00的4H结果 |
| EUR双侧利差 | ECB公开历史与Treasury | 新增轻量Provider后估代理利差关系 | 代理spot/par差不是同期限OIS预期差 |
| 宏观增长/通胀/流动性 | FRED/ALFRED、Eurostat/ECB | 有vintage与release才可回溯研究 | 最新修订历史不能重建当年可知信息 |
| COT | 现有Gold商品报告；官方历史可请求 | 固定类别/合约后周频极端与flow统计 | 当前Provider不能覆盖所有金融资产；同一周填5次不等于5次独立持仓冲击 |
| Deribit Funding | 官方小时历史接口，本项目未封装 | 增量接入后做费率分布与前瞻检验 | current_funding不能替代已实现funding序列 |
| Deribit OI/Basis/Skew历史 | 当前快照Provider | 从今开始归档；核实可授权历史后再回填 | 不能承诺能免费补全过去数年surface/OI |
| Gold/FX/DXY期权 | 仅当前ETF代理链 | 风险context和前向归档 | 不是现货OTC历史，也不能立刻估regime beta |
| 事件surprise | 有日历接口但无配置/冻结consensus库 | 先建发布前consensus归档与首次actual | 今天查到的consensus/actual不保证当时版本 |
| Prediction markets | 当前市场/盘口可读 | 按规则白名单采集、研究事件特征 | 不同寿命、规则、流动性的合约不能直接拼成长期概率因子 |
| 地缘/文本 | 无确定性合格feed | 可引用事实、风险标签；注册文本研究任务 | LLM觉得“严重”不能变成可复现数字 |

日频历史可获得≠08:00截点历史可获得≠数据当时已发布。若只能构建日收盘研究，就建立独立 `EOD_RESEARCH` cohort；其结论不得直接给08:00 H4模型认证。

## I. 去重与组合约束清单

| 可能重复 | 初始处理 | 升级验证 |
|---|---|---|
| 5D/20D Momentum、MA、Slope、Persistence | 共用trend block，Persistence仅门控 | 先做整块消融，再做叶级 |
| U.Y2与U.REL2 | 一个rates簇；预算拆分而非两票 | 联合回归检查条件数与增量，优先删冗余 |
| Gold nominal10/real10/breakeven | real独立方向，其余背景 | 改成两维正交基后才重分配 |
| EURUSD与DXY | EUR模型用USD_EX_EUR，原DXY仅展示 | 对残余美元与EUR自身动量做联合检验 |
| SP500与Nasdaq | 主风险块+NDX residual | 残差变换必须训练内估计 |
| VIX、HY OAS、股票下跌 | 同一个risk family | 家族消融，避免同一恐慌重复加置信 |
| CPI surprise、US2Y变化、PM Fed变化 | 共用event/monetary lineage标签 | 比较surprise→响应的增量，而不是三个“鹰派”投票 |
| Treasury与FRED DGS/DFII，Yahoo与Stooq/OpenBB | 同一个数据源血缘 | 只评备用源稳定性，不增经济权重 |
| BTC price与USD OI | inverse用固定面额合约数；只有线性市价估值才还原base units | 比较合约数量变化与price交互；禁止因估值或错误换算误判新资金 |

树的完整性验收不是“每个叶子都亮绿灯”。验收应是每个叶子都有明确ID、数据终点、时间频率、数学路径、角色、权重与启用条件，未满足的能被看见并对最终判断产生恰当约束。

## J. 未来Brent的扩展边界

未来若注册Brent，专属分支需加入EIA/IEA库存与供需、OPEC官方决定、产量、裂解价差、期货期限结构以及运输通道事件。每个叶子仍须遵守本规格的数据终点、数学函数和PIT规则；本轮不将这些变量混入四资产核心，也不创建Brent模型。
