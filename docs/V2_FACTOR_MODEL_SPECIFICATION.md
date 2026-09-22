# Digital Oracle V2 — 资产判断说明书

规格版本：Draft 1.0 · 2026-09-17。状态：供研究者审阅的设计，尚未实现、估计参数或回测。文中的初始参数是可证伪的研究先验，绝不是已证明有效的参数。

配套文件：[四资产因子树与叶节点目录](V2_ASSET_FACTOR_CATALOG.md)、[当前项目状态](../ARCHITECTURE_SNAPSHOT.md)。正文定义统一计算与验证契约，目录逐项指定数据、公式、期限、角色和初始权重；两份文件共同构成完整规格。

## 1. 研究者首先应该知道什么

V2 的研究问题是：截至某一时刻真实可获得的信息，对某一明确标的未来 4H、1D、3D、5D 的变化是否提供稳定的增量信息？哪些信息只能解释当前背景，哪些能够改善前瞻判断？

本次用户指令明确扩展了旧盘前模式：允许确定性的技术因子、分期限方向研究和事后验证。继续保留六模块 Market Context 展示，增加模型解释视图；不设计下单、持仓管理或入场路径。旧 AGENTS.md、Skill 和 Web 提示词仍含禁止方向研究的边界，实施时须版本化调整，不能把本规格误称为当前已具备的能力。

读一个叶节点，应能回答九件事：测量什么、来自哪里、何时已知、变化多大、如何标准化、方向依据是什么、为何获得该权重、今天贡献多少、过去是否有效。读不到其中一项，就应显示缺口。

### 1.1 三种数字必须分开

| 数字 | 含义 | 可否评价未来方向 |
|---|---|---|
| Context Score | 对已发生变化的标准化描述、理论压力或同步统计关联 | 单独不可以 |
| Predictive Evidence Score，简称 E | 用截点前信息对指定未来期限的证据汇总，范围 [-2,2] | 可以冻结后检验；不是收益率或概率 |
| Risk / Data Quality | 波动、事件密度、时效、缺失和可比性 | 决定是否弃权、结论边界；不能机械提供方向 |

比如实际利率上涨与黄金过去一周下跌同现，只能支持解释关系。只有“截点前实际利率变化”在时间外样本中能解释“截点后黄金收益”，才能支持预测关系。二者分别存储 `beta_explain` 与 `theta_predict`，禁止混用。

高 E 也不等于高置信度。模型可能在错误或重复的证据上高度一致。可靠性来自冻结后的结果与覆盖率，不能由 AI 自评产生。

### 1.2 范围与平衡

| 关系 | 当前选择 | 失衡警报 |
|---|---|---|
| 因子完整性 / 可估计性 | 树完整，未满足条件的叶子保持 disabled 或 context_only | 仅因树上有节点就分配方向权重 |
| 经济先验 / 数据证据 | 弱先验启动，外样本验证后升级 | 一次错误就改符号；样本内收益决定一切 |
| 解释 / 预测 | 两套系数、两个结果字段 | 同期 beta 被当作未来预测系数 |
| 细分 regime / 样本量 | 初始最多一个连续压力交互，报告粗分组 | 每个资产×期限×状态只有几个样本却调权 |
| 独立运行 / AI 研究 | Python 完成必要链路；AI 注释可缺席 | 模型服务超时导致当天无账本记录 |
| Accuracy / Coverage | 同时报全部机会、有效机会、发声与弃权 | 通过隐藏困难日期来提高准确率 |

## 2. 标的、时钟和预测对象

### 2.1 Asset ID 不是页面名称

| 页面 | V2 主研究标的 | 现有数据 | 必须处理的差别 |
|---|---|---|---|
| USD | DXY 指数，`USD.DXY.INDEX` | Yahoo `DX-Y.NYB` | 这是固定篮子美元指数，不是所有美元资产；DTWEXBGS 广义贸易加权美元只能作另一个因子 |
| EURUSD | USD per EUR 现货，`FX.EURUSD.SPOT` | Yahoo `EURUSD=X` | 正收益表示欧元升值；报价源及日界线须固定 |
| Gold | 目标是 USD/oz 的 XAUUSD 现货，`METAL.XAUUSD.SPOT` | 当前 `GC=F` 是黄金期货代理 | 在合格现货源到位前，独立运行 `METAL.GC.CONTINUOUS.PROXY`；不合并命中率，不悄悄切换到现货 |
| BTC | USD 报价现货参考，`CRYPTO.BTCUSD.REFERENCE` | Yahoo `BTC-USD`；Deribit 指数为衍生品配套参考 | USD 与 USDT、单交易所与聚合指数不是同一标的；必须锁定 outcome source |

Gold 的生产发布有数据契约门槛：明确现货报价源、历史覆盖、许可、交易时间和价格字段。当前不虚构一个已有 XAUUSD 接口。GC 代理历史可以做探索，但连续合约换月规则未审计前不能成为“已验证 Gold”模型。

DXY 中欧元权重为 57.6%，故 DXY 与 EURUSD 不能当作两份独立美元证据。该机械关联是资产设计约束。[ICE 方法](https://www.ice.com/publicdocs/data/ICE_FX_Indexes_Methodology.pdf)

### 2.2 每日冻结与期限

建议首个研究 cohort：每天纽约时间 08:00 截断特征，08:05 前完成冻结；先服务一个统一截点。新增伦敦或亚洲截点必须另建 cohort，不能当作增加了独立交易日样本。

| Horizon ID | 定义 | 初始特征用途 |
|---|---|---|
| H4（页面 Intraday / 4H） | 从基准价格时刻起，经过 4 个 UTC 小时 | 完成的1小时观测、即时跨市场与衍生品、当天事件；不是5分钟交易引擎 |
| D1 | 非 Crypto：下一个该标的有效交易日的相同当地时刻；BTC：24个UTC小时 | 短趋势、已发布宏观变化、衍生品 |
| D3 | 非 Crypto：第3个有效交易日相同时刻；BTC：72个UTC小时 | 趋势、利差、跨市场、持仓背景 |
| D5 | 非 Crypto：第5个有效交易日相同时刻；BTC：120个UTC小时 | 同上，慢数据预算可提高 |

非 Crypto 以版本化 `asset_calendar_id` 判定有效交易日。DST 导致 D1 不一定等于24小时。BTC 可每天形成记录，但周末传统市场 closed 的事实会影响跨市场证据；周末须单独报告表现。

流程的五个时间：

1. `scheduled_cutoff`：预定 08:00；所有输入 `available_at <= cutoff`。
2. `snapshot_sealed_at`：输入包封存；晚到的数据即使 observation_time 更早，也不进入本次 live 包。
3. `issued_at`：确定性判断持久化成功，预测正式生效。
4. `baseline_time`：issued_at 之后第一个合格报价，5分钟内；等待报价不能修改已冻结判断。
5. `target_at`：从 baseline_time 按上述期限计算，生成时即登记算法和日历版本。

若08:05仍未冻结，记录 missed/late_run；可以生成新的 late cohort，但禁止伪装为08:00正式预测。电脑休眠后补采也不能重建一份“当时已发布”的 live 判断。

### 2.3 Price Contract 与观察窗

- 默认评价价格为固定来源的 midpoint；来源无 bid/ask 时，另定 `reference_last` 合约并显式标明。指数只评估参考指数变化，不能称为可交易收益。
- baseline 报价市场时间必须不早于 issued_at，并在5分钟内出现；市场时间不可用或显著延迟时，该预测标为 baseline_missing，仍保留在全部机会分母。
- outcome 取 target_at 之后60秒内第一条合格报价；必须保存实际偏差。若源仅有1小时柱，则注册单独 `bar_close_1h` 评价契约，预先定义柱边界，不能与报价契约混报准确率。
- H4 target 处于闭市且无法取得合格报价时，结果为 not_evaluable_closed；禁止自动移到下个开盘而仍叫4H。D1/D3/D5按资产日历预先安排。
- 事后可下载“目标时刻的历史报价”补齐，不能用下载时最新价格。超过宽限期后仍缺失，保留 outcome_missing；后来取得数据可追加结果修订，原版本不删。
- 只使用截点前完成的 OHLC bar。当天尚未完成日线不能进入日线 MA/ATR。即时快照放在另外的特征字段。
- FX日线先以现有源的正式日界为探索口径，审计后注册；切成纽约17:00日线需要有足够小时历史且生成新数据版本。BTC日线固定UTC 00:00；跨资产组合使用共同可得截点，不直接拼接同名日期。

## 3. 证据契约与数据治理

每次原始观察至少记录：`series_id, instrument_id, value, unit, currency, observation_start/end, released_at, source_updated_at, first_seen_at, fetched_at, available_at, time_precision, frequency, expected_next_release, freshness, status, source_url, provider_version, payload_hash, revision_id, lineage_id`。

`released_at` 是发布时间；`observation_end` 是统计所属时期。COT周二持仓不能在周二模型中使用。月度通胀不能按月末日期提前加入。live 的 `available_at = max(released_at（可信时）, first_seen_at)`；回溯重建使用可证明的历史发布时间和当时 vintage，并注明 `reconstructed`，不能伪造 first_seen_at。

只有日粒度 vintage 时，无法证明同日08:00已知的数据，保守从下一有效研究日使用；不从午夜启用。FRED 默认给今天所知历史；历史重建要使用 ALFRED real-time/vintage，不能默认最新修订值。[FRED 时间语义](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)

### 3.1 Reliability Weight 是工程权重

初版确定性约定（均进入 manifest；不代表统计置信概率）：

```
Q = q_time × q_unit × q_lineage × q_market × q_completeness
```

- `q_time`：正常发布周期内=1；超过预期发布时点加 grace 后按 `2^(-overdue/half_life)` 衰减；超过2个周期=0。quotes grace=60秒、half_life=5分钟、超过30分钟=0；官方日频 grace=1业务日、half_life=1业务日；周频 grace=1发布业务日、half_life=1周；月频 grace=2业务日、half_life=1月。未核实发布日程的时间质量为 unknown，Q=0用于预测。
- `q_unit`：单位与合约已核实=1；否则0。不能把美元名义OI与币数OI直接相加。
- `q_lineage`：可回溯原始载荷/授权数据文件=1；原始历史可读但修订状态不明=0.5仅可探索；新闻摘录数值或无法溯源=0。
- `q_market`：普通非衍生品=1；options/prediction market 通过第7节价差、深度和期限规则=1，否则0。
- `q_completeness`：叶子所需输入齐全=1，否则0。可选诊断字段不影响；核心输入不能默认0。

freshness 与 frequency 分开：昨天财政部数据可能“仍是最新发布”，但绝不因此变成实时利率；其 H4 权重可以为0。闭市并不自动等于 Provider 失效，UI分别显示 closed/latest_official/stale。

数据源质量不能奖励重复：同一上游的 Yahoo、Stooq兼容层与OpenBB-Yahoo共用 `lineage_id`；FRED转载财政部曲线也不算第二份证据。独立市场来自相同供应商可以含不同经济信息，但共享供应商故障风险，分别保留 `economic_cluster` 与 `vendor_cluster`。

## 4. 数学字典：所有叶子共用的精确定义

### 4.1 记号、标准化与暖机

`t` 是最后可得且合格的观测；D表示该序列的有效观测日，W表示周报告。收益全用小数对数收益 `r_k(P)=ln(P_t/P_{t-k})`。利率原值若为百分数，`bp_k(y)=100×(y_t-y_{t-k})`，例如2.00→2.10是10bp。

所有统计窗结束于 t 之前，不把当前冲击算入自己的历史尺度。日频默认 W=756观测、最少504；小时频 W=1440完成柱、最少720；周频 W=156、最少104；月频 W=120、最少60；发布 surprise 最多60次、至少36次同一种发布。方差为0、样本不足或输入非有限数：score=null，status=warmup/invalid，不伪造0分。

```
Z_W(x_t) = clip((x_t - mean(x[t-W:t])) / sample_std(x[t-W:t]), -5, 5)
P_W(x_t) = (#历史值<x_t + 0.5×#历史值=x_t) / N
RZ_W(x_t) = clip((x_t-median_history)/(1.4826×MAD_history), -5, 5)
B(z) = 2×tanh(z/1.5)                         # [-2,+2]
L(x) = 2×P_W(x)-1                            # [-1,+1]
V(x) = 2×P_W(x)                              # [0,2]，风险，不加到方向分
```

规则选择：近似平稳的收益/收益率变化用Z；Funding、Basis、OI变化与事件 surprise 的重尾分布用RZ；持仓极端与波动状态用percentile；趋势距离用ATR归一化；跨市场敏感度用滞后训练的多元回归。MAD为0不自动回退到另一种变换；变换更改须新版本。

Z测量“相对过去平均的异常”，不等同于“是否上涨”。实际利率上涨1bp，而过去5D变化均值为+3bp时，Z可为负。页面同时展示原始变化和异常分数，不写成利率下降。

### 4.2 技术叶子模板 T（四资产各自实例化）

价格来自资产自己的 Price Contract。生产前先审计复权、缺口、换月和时区。`s`为标准化输入；Context Score为B(s)。下表没有赋予ATR/RV方向。

| 叶子后缀 | 原始值与完整变换 | 频率/窗 | 初始角色与份额 |
|---|---|---|---|
| MOM5 | `m5=r_5(P)`；`s=Z_W(m5)` | 日频；H4另用4个完成小时柱的 `r_4` | 与MOM20同一 momentum block，总份额0.60 |
| MOM20 | `m20=r_20(P)`；`s=Z_W(m20)` | 日频；H4另用20个完成小时柱的 `r_20` | 同上，不能作为第二个独立确认 |
| SLOPE | 对最近5个已完成观测的 `m5` 对序号0…4作含截距OLS；`s=Z_W(5×slope)` | 日频或H4小时序列 | trend block份额0.20；衡量动量加速度 |
| MA | `(SMA_5(P)-SMA_20(P))/ATR_14`；`s=clip(value,-5,5)` | 日频或H4完成小时柱 | trend block份额0.20；衡量均线分离程度 |
| ATR | `TR=max(H-L,abs(H-Cprev),abs(L-Cprev))`；ATR14以首14个TR均值启动、之后Wilder递推；`x=ATR14/C`；risk=`V(x)` | 日频；H4小时频 | 方向权重0，风险尺度与MA输入 |
| RV | `rv20=sample_std(r1,last20)×sqrt(A)`，A=252（FX/DXY/Gold）或365（BTC）；小时频使用相应全年计划有效柱数 | 日频/小时频；risk=`V(rv20)` | 方向权重0；目标收益缩放和状态 |
| PERSIST | `ER20=abs(P_t-P_t-20)/sum(abs(P_j-P_j-1),20)`；分母0→invalid；context=`2×ER20` | 日频/小时频 | 方向权重0；已存在趋势贡献的门控 `g_trend=0.5+0.5×ER20` |

momentum block内部 `(MOM5,MOM20)` 比例：H4=(0.75,0.25)，D1=(0.65,0.35)，D3=(0.50,0.50)，D5=(0.35,0.65)。组合 `s_mom=a×s5+(1-a)×s20` 后才进B，避免重复计分。SLOPE、MA仍属于同一趋势簇，不能提高独立证据数量。

T的初始方向先验为顺趋势，但证据弱，统一 `theta_prior=+0.25`；不是引用文献得到的短周期最优系数。只生成 provisional 研究判断。技术叶子若取得真实小时数据，可用于H4；当前 YahooPriceProvider 仅支持日/周/月，小时研究需要扩展历史契约，不能拿当前5天快照充当两年小时历史。

### 4.3 利率、宏观、相对差异模板

| 模板 | 完整定义 |
|---|---|
| RATE(k) | `x=bp_k(y)`；`s=Z_W(x)`；默认k按H4/D1/D3/D5=(1,1,5,20)，日频利率H4仅背景 |
| CURVE(k) | `x=100×[(y10-y2)_t-(y10-y2)_{t-k}]`；`s=Z_W(x)`；同k |
| SPREAD(k) | `x=100×[(y_EU-y_US)_t-(y_EU-y_US)_{t-k}]`；共同日期、共同可用截点；`s=Z_W(x)` |
| LEVEL | 对最新水平给 `s=L(x)`；仅作慢状态，除非独立预测验证，不把高利率水平自动当作明日上涨 |
| MACRO_ACCEL | 月度价格指数先 `pi3=400×ln(index_m/index_m-3)`；`x=pi3_m-pi3_m-3`；`s=Z_120(x)`；增长用工业产出指数同样公式 |
| REL_GROWTH | US/EU各自工业产出 `g3=400×ln(IP_m/IP_m-3)`；各用月度历史Z，再 `s=(Z(g_EU)-Z(g_US))/sqrt(2)`；最近共同参考月份；存两侧发布时间 |
| BALANCE | `x=(A_t-A_t-4W)/abs(A_t-4W)`；`s=RZ_156(x)`；用周频已发布资产规模 |
| NET_LIQ | 以同一已知周截面，将WALCL/1000、WDTGAL/1000、RRPONTSYD统一到十亿美元；`N=WALCL/1000-WDTGAL/1000-RRP`；`x=(N_t-N_t-4W)/(WALCL_t-4W/1000)`；`s=RZ_156(x)` |
| SURPRISE | `raw=first_actual-consensus_frozen_before_release`；在此前最多60次、至少36次同类首次surprise中，`MADscale=1.4826×median(abs(raw_history-median(raw_history)))`；`u=raw/MADscale`；`s=clip(u,-5,5)×2^(-age_hours/24)`；MADscale=0则invalid。保留零意外原点，不减历史均值；修订冲击另存 |

NET_LIQ 是研究代理，不是会计恒等式意义的“市场可投资美元总量”；不能将TGA/RRP变化一比一解释为风险资产买盘。WALCL、TGA、RRP及其合成量共用一个 liquidity block，不能合成和分量各占一票。

收益率曲线和 real/nominal/breakeven 存在线性依赖。Gold初始以实际利率与DXY为主；nominal10与breakeven作为解释分解，不与实际利率同时独立重权求和。若加入breakeven，须以正交化或组约束验证增量。

### 4.4 回归：解释与预测各有任务

解释回归在对齐的已完成窗口估计：`r_A,d = alpha + beta_real×delta_real_d + beta_usd×r_DXY,d + beta_risk×r_SPX,d + error_d`。利率单位为bp；只使用最新拟合截点之前的数据，默认252个共同日，最低126，输出置信区间、条件数和残差。它描述统计关联，不声称因果，也不自动生成预测。

预测回归使用：

```
y[u,h] = ln(P_endpoint/P_baseline) / sigma_hat[u,h]
phi[u] = 在u的cutoff真实已知的标准化因子
theta = argmin sum((y - alpha - Phi×theta)^2)
                  + lambda×sum((theta-theta_prior)^2)
effect[j,t,h] = (theta[j,h] + eta[j,h]×stress[t]) × phi[j,t]
factor_score[j,t,h] = B(effect[j,t,h])
```

lambda在内层时间滚动验证选自冻结小集合 `{1,10,100}`，不扩展网格直到结果好看；所有输入先按训练窗规则缩放。eta初始0；只有注册过且外样本支持的交互才开放。截距是单独 `BASE_RATE` 节点，初版固定0，未来若拟合必须展示。

上式明确区分两个输出：线性模型的 `y_hat=alpha+Phi×theta` 是标准化收益的研究预测；第6节经有界变换、家族预算与Q调整的E是另一种证据指数，不等于y_hat，也不能反推为预计涨跌幅。模型晋级必须检验最终发布的E及其弃权规则；线性回归表现好不能替代E的时间外验收。引入eta时把 `phi×stress` 明确作为额外设计矩阵列，加入同一个拟合目标，先验0、同lambda惩罚，并计入参数上限。

训练样本必须满足 endpoint 和 outcome 数据在训练截点已可得。D5模型最后5个未兑现样本不能进训练。训练窗起始建议756个研究日、最低504个有效日；H4要求至少250个不同研究日而非250根相关小时柱。参数数量上限 `p <= floor(N_eff/20)`，同时最多8个独立方向特征块；不足则保留先验或0，不能在几十个样本上拟合整棵树。

`beta`、`theta`和`eta`默认按月重新估计为候选版本。日常滑动Z、percentile及regime随新数据改变属于冻结算法的正常计算；每日不得重新优化权重。候选参数投入正式计算即生成新版本。

如果理论的负向实际利率关系在预测回归中不稳定，允许theta收缩至0；不能强迫它永远负向，也不能根据一次结果把先验改成正向。变号必须显示理论冲突和跨折稳定性。

## 5. Regime：少量连续状态与解释标签

V1只开放一个可估计交互轴 `stress`，其他状态先用于分组和显示。所有轴只用截至cutoff的信息；缺失显示unknown，不能用未来数据填补。

```
stress = clip((P756(VIX_level)+P756(HY_OAS_level))/2, 0, 1)
trend_strength = ER20
inflation_state = tanh(Z120(US_inflation_accel)/1.5)
policy_state = tanh(Z756(bp20(US2Y))/1.5)
liquidity_state = tanh(RZ156(net_liq_change4W)/1.5)
growth_state = tanh(Z120(US_IP_growth3M)/1.5)
```

上述默认输入固定为：VIX=Yahoo `^VIX`最后已完成日值，HY=FRED `BAMLH0A0HYM2`；inflation_accel=CPILFESL按MACRO_ACCEL计算，IP_growth3M=INDPRO的 `400×ln(IP_m/IP_m-3)`。月频Z120按月度有效发布观测计算，绝不按每日前向填充值增加样本。切换VIX源或状态频率须修改manifest；小时VIX冲击可以独立展示，不偷偷替换该日频状态轴。

HY缺失时可以定义另一个 `VIX_only` regime规格，但不能在同一版本每天临时换公式。BTC周末沿用最新官方风险数据时，状态标为slow_context，不伪装为周末实时压力。

统计显示压力低/中/高阈值为0.3/0.7；连续值用于交互。V1不交叉展开6个轴造成稀疏状态爆炸。方向系数对状态的影响放在 `theta+eta×stress` 内，不能再重复乘另一个主观“regime multiplier”。若采用统一的乘子表达，必须是此公式的等价展开，且theta=0时不可除零。

避险并非固定“VIX↑→Gold↑”：流动性冲击时可同跌。BTC Funding在温和区间可能描述需求，极端区间可能描述拥挤；这些是假设而非内置真理。允许最多一个预注册非线性扩展 `hinge(x)=max(x-q90_train,0)`，相应参数需要新版本和独立验证。

## 6. 初始权重与聚合

### 6.1 权重是什么

预算B限定一个经济家族最多能影响多少。叶内alpha是防止重复的分配。theta是历史敏感度或明确标出的弱先验。Q是数据可信度。它们不应互相冒充。

```
c_j = B_family × alpha_j × Q_j × B(effect_j)
E_asset,h = sum(c_j)             # B预算和<=1；alpha组内和<=1，因此E在[-2,2]
```

趋势项额外乘g_trend，但不能再把PERSIST加一次方向分。共同原始输入、多期限变化、同一政策事件的派生量以block预算限制。未启用的叶子分数null、贡献0并带理由；预算不自动转给其他因子。方向权重为0的风险节点仍显示Current Value、Transformation、Risk Score、Weight=0、Contribution=0及作用对象。

技术块的精确展开为 `c_T=B_T×g_trend×[.60×Q_mom×B(theta_mom×s_mom)+.20×Q_slope×B(theta_slope×s_slope)+.20×Q_MA×B(theta_MA×s_MA)]`（允许交互时替换对应theta）。`Q_mom=min(Q_MOM5,Q_MOM20)`，任一必要输入缺失则整块momentum不可用；PERSIST缺失则整个T块不可用。MOM5/MOM20在树上显示各自数值与组合系数，但最终贡献归属于共同MOM block，不将非线性B后的贡献伪拆成两个可加独立分数。

禁止逐日根据“今天有数据的项”重新归一化到100%。否则断掉利率源反而会让技术面自动变强。允许研究者为不同部署配置注册一个更小的独立模型版本，不能临时换分母。

### 6.2 候选家族预算（设计先验，不是最优权重）

T=技术，M=宏观/利率/美元，X=跨资产，P=持仓/衍生品，E=事件方向。风险事件门控不消耗方向预算。预算表达研究优先级；实际未验证家族会保留未使用容量。

| 资产 | Horizon | T | M | X | P | E |
|---|---|---:|---:|---:|---:|---:|
| USD | H4 | .35 | .30 | .20 | .00 | .15 |
| USD | D1 | .30 | .35 | .20 | .05 | .10 |
| USD | D3 | .25 | .40 | .15 | .10 | .10 |
| USD | D5 | .20 | .45 | .15 | .10 | .10 |
| EURUSD | H4 | .35 | .35 | .15 | .00 | .15 |
| EURUSD | D1 | .30 | .40 | .15 | .05 | .10 |
| EURUSD | D3 | .25 | .45 | .10 | .10 | .10 |
| EURUSD | D5 | .20 | .50 | .10 | .10 | .10 |
| Gold | H4 | .40 | .30 | .15 | .05 | .10 |
| Gold | D1 | .35 | .35 | .10 | .10 | .10 |
| Gold | D3 | .30 | .40 | .10 | .10 | .10 |
| Gold | D5 | .25 | .40 | .10 | .15 | .10 |
| BTC | H4 | .35 | .10 | .20 | .25 | .10 |
| BTC | D1 | .30 | .15 | .20 | .25 | .10 |
| BTC | D3 | .25 | .20 | .20 | .25 | .10 |
| BTC | D5 | .20 | .25 | .20 | .25 | .10 |

这些数值仅用于可复现的初始比较：EURUSD重两侧利差、Gold重实际利率与美元、BTC保留较大衍生品预算；没有证据支持精确到0.05优于其他值。必须与简单等块权、仅趋势、零预测基线比较；若无增益，保留更简单模型。E预算不会因有新闻而自动激活。

家族内部初始分配见因子目录。只有目录标 `A` 的节点有弱方向先验；标 `R` 的节点初始theta=0，完成训练/验证后由新版本激活；标 `C/K` 分别是仅背景/风险门控、方向权重0。必要数据未满足时A也输出missing。H4中的日频利率节点初始仍只作背景，M的预留容量不转移。

### 6.3 结论状态与 Edge

将不同问题保存为不同字段，避免Neutral和No Edge互相覆盖：

- `directional_view`：Positive / Negative / Neutral，初始阈值 `abs(E)>=0.35` 才有方向，属provisional。
- `evidence_state`：Aligned / Mixed / No Clear Driver / Insufficient Data。
- `edge_state`：No Edge / Candidate / Validated；UI中的“有Edge”默认只指Validated。
- `validation_status`：prior_only / research_oos / forward_validated / degraded。

数据门槛先于方向分类：有效数据预算覆盖不足0.80或必需输入缺失时，`evidence_state=Insufficient Data`、`directional_view=null`、`edge_state=No Edge`。仍可展示partial_E和已算贡献，但不能把缺失填0后得到的E=0叫作Neutral。预算覆盖精确定义为 `sum(B_family×alpha_j×Q_j)/sum_enabled(B_family×alpha_j)`，以方向block计；未通过PIT验收的探索数据不进入生产分子。分母=0则unknown。

冲突度 `conflict=1-abs(sum(c))/sum(abs(c))`；分母0→null。若conflict>=0.6且正/负总贡献各>=0.1，标Mixed；如果有效贡献绝对和<0.15，标No Clear Driver。独立支持要求至少两个经济簇，各自同向绝对贡献>=0.05；同一趋势的MA/动量不算两个。

Candidate门槛：abs(E)>=0.35、有效数据预算覆盖>=0.80、必需源齐全、非Mixed、两个独立经济簇支持、无事件/数据硬门控。coverage按模型声明的enabled预算计算，同时展示enabled/总设计预算；不能靠禁用所有缺数据因子提高表面覆盖。

各版本必须显式列出required_inputs：至少包括本标的价格/收益尺度、已启用方向块的必要输入和使用中的regime输入；H4还必须有合格事件日历。事件日历unknown不能当作无事件绕过门控。所有正式预测输入要求已审计血缘与时点；q_lineage=.5仅产生独立exploratory记录，不能获得Candidate/Validated。对于有多源替代的输入，替代序列和切换规则必须事前版本化。

Validated还需资产×期限满足第11节外样本/实盘门槛；regime样本不够只能说整体通过，不能说该状态有效。未验证模型可以每天冻结方向并评价，但不能把Candidate当成统计意义的已知交易优势。

## 7. 衍生品、事件及信息的专门公式

### 7.1 Positioning / Derivatives

| 模板 | 数据要求和算法 | 方向规则 |
|---|---|---|
| COT | 固定report type、contract market code、trader class；`net_share=(long-short)/OI`；level=`L156(net_share)`；flow=`RZ156(delta4W(net_share))` | level为拥挤背景C；flow为R，不把机构等同聪明钱 |
| FUND | 固定BTC-PERPETUAL；过去24个完整、不重复小时的 `interest_1h` 累加：`f24=sum(interest_1h)`；s=`RZ1440(f24)`；这是24h报价费率汇总，不假定资金费自动再投资 | R；缺小时则invalid；未满足历史字段时不能拿current_funding代替 |
| OI | 初版固定Deribit inverse BTC-PERPETUAL。按合约metadata将USD单位OI除以USD合约乘数得到 `n_contracts`；`s=RZ1440(log(n_t/n_t-24h))`，n<=0则invalid | R；OI是多空配对未平仓量，不直接赋正号。线性币本位数量另注册factor，不混聚合 |
| BASIS | 同期到期合约相对spot index：`b(T)=ln(F_T/S)×365/days_to_expiry`；在夹住30天的两个合约间线性插值年化b；s=`RZ1440(b30)` | R；近到期<7天不用于30D估计。当前项目basis_vs_perpetual不能改名成spot basis |
| IV | 期限T的ATM forward implied variance `w(T)=IV(T)^2×T`；用夹住30D的两期限线性插值w，再 `IV30=sqrt(w30/(30/365))`；风险=`V(IV30)` | K；无方向 |
| SKEW | 同一期限25-delta put IV减call IV，插值到30D；s=`RZ(Skew30)` | R，符号交给预测验证；不是“put多所以必跌” |
| VRP | `IV30^2 - RV20_annual^2`；s=`RZ(value)` | C/K；IV未来与RV过去不同，不能当已实现风险溢价收益 |

options须保留报价、IV来源、模型和delta convention。ETF期权delta采用含股息Black-Scholes，期货期权采用Black-76，Crypto采用来源明确的forward/delta定义；不能混用。目标两侧delta和期限不被数据夹住时不外推。报价必须双边、正价、未交叉，`spread/mid<=0.25`，OI>=100合约、剩余7…90天；这些是待验证的数据门槛，并非流动性保证。缺delta时需扩展ticker输入或确定性反解，不能让LLM估计。

OI单位尤其不能一律“除价格去估值”：inverse合约的USD面额本来固定，除以BTC价格反而引入机械反向价格项。只在上游确实给出线性持仓的按市价美元估值时，才除同步价格还原base units；inverse统一用合约数变化，BTC等值只作敞口展示。OI门槛也先换成真实合约数，而非直接比较API原始字段。[Deribit合约单位](https://support.deribit.com/hc/en-us/articles/31424954847133-Inverse-Perpetual)、[行情字段](https://docs.deribit.com/api-reference/market-data/public-get_book_summary_by_currency)。

### 7.2 Event / Information

- **临近风险 EVT**：正式日历中，与资产相关且在预测区间内的事件，重要度固定为高=1、中=.5；`risk=2×[1-exp(-sum(importance×exp(-hours_to_event/24)))]`。没有合格日历=unknown，不是0。H4若未来4h内有高重要度央行决议/CPI/NFP，初版Candidate强制关闭；D期限显示风险，是否门控由独立事件研究决定。
- **发布 surprise**：使用SURPRISE模板；CPI核心环比、PCE核心环比、NFP首次新增就业、欧元区HICP首次同比分别统计，不混单位和样本。市场consensus必须在公布前冻结；Forecast与供应商模型预测字段不能混用。无consensus时只展示actual/previous与变化，不生成surprise。
- **央行决定**：`u=(actual_policy_change_bp-expected_change_bp_frozen)/25`；score输入=`clip(u,-5,5)`再按24h半衰期衰减。expected须来自期限匹配的完整离散政策结果市场/OIS报价契约；只有一个“会不会降息”合约时不足以计算期望政策变动。无预期就保留实际决定背景，方向贡献0。
- **声明/讲话**：官方来源、发布时间、文档hash和受控标签只作C；程序评分固定null，贡献0。AI可提出研究假设，不能临场改鹰鸽分。未来若引入文本指标，应冻结词典/模型版本并单独做PIT验证。
- **地缘政治 GEO**：版本化事件表，只有正式来源可核实事件进入；type权重如已确认制裁=.5、运输中断=1、武装冲突升级=1，仅表示风险；`risk=2×[1-exp(-sum(weight×exp(-age_hours/72)))]`。按独立事件ID去重，同一新闻转载不增加风险。无人维护或没有合格feed则unknown；不假设未抓到消息=无风险。初始方向贡献0。
- **Prediction Market PM**：按市场规则和期限白名单固定condition/token；价格取同期best bid/ask midpoint。价差<=.05、24h成交额>=100000 USD且距中价±.02双侧挂单名义深度各>=10000 USD，更新<=5分钟；任何字段缺失不启用。`p=clip(mid,.02,.98)`；`u=logit(p_t)-logit(p_t-24h)`；s=`RZ(u)`，至少180天同口径连续历史且未改规则才估计。初始R/0权重；若合约寿命不够，仅C，不能跨不同结算问题拼历史。

PM是交易价格隐含信息，包含风险偏好、摩擦与合约规则；不是事实概率。Polymarket/Kalshi同一事件共用event cluster，与该事件后的收益率反应也须做重复控制。任何不符合门槛的节点明确disabled及原因，不削弱规则来凑满树。

## 8. Gold 实际利率：从原始数到贡献的完整例子

以下全部是演示数值，不是市场实测或回测估计。观察10Y TIPS日频实际收益率，5个已发布观测日变化+10bp。此前756日的5D变化均值0bp、标准差8bp：

```
delta5 = 100×(2.10%-2.00%) = 10bp   # 公式中的存储值为2.10与2.00
z = (10-0)/8 = 1.25
context_pressure = -2×tanh(1.25/1.5) = -1.3645
```

| 5D变化 | 历史标准差 | z | 理论背景压力分 |
|---:|---:|---:|---:|
| +1bp | 8bp | .125 | -.1663 |
| +10bp | 8bp | 1.25 | -1.3645 |
| +30bp | 8bp | 3.75 | -1.9732 |
| +10bp | 20bp | .50 | -.6430 |

这解决“变动是否异常”，尚未解决“未来是否继续反应”。假设另一个已经冻结的预测版本得到D3标准化收益系数theta=-.30、压力交互eta=+.10、当日stress=.50：

```
effective_theta = -.30 + .10×.50 = -.25
effect = -.25×1.25 = -.3125
predictive_factor_score = 2×tanh(-.3125/1.5) ≈ -.4107
B_M=.40; alpha_real=.60; Q=1
contribution_real = .40×.60×1×(-.4107) ≈ -.0986
```

假定其他不重叠贡献是趋势+.18、美元-.06、跨资产+.02、持仓0、事件0，E≈+.0414。结论为Neutral且No Edge，并同时显示实际利率逆风与技术证据冲突。不能因为树上许多叶子“偏强”就输出强方向。

假设压力state下系数变弱只为说明计算方式；本轮没有估计出-.30或+.10。真正初版先验theta=-.25、eta=0，或者在数据未通过PIT审计时完全停用预测贡献。

## 9. Prediction Ledger：历史判断只能追加

SQLite足以启动单机研究，但需要明确的事务、幂等、约束和备份。`snapshots.py`现有HTTP测试录放功能不是研究账本，不应直接冒充Prediction Ledger。

| 表/对象 | 核心字段与不变量 |
|---|---|
| `model_versions` | model_id、asset、horizon、parent_id、manifest_json、code_hash、feature/normalizer/calendar/evaluation版本、训练截止、数据hash、状态；版本内容只增不改 |
| `model_events` | candidate/approved/activated/retired的追加事件、操作者、时间、原因；激活状态不靠覆盖manifest |
| `runs` | run_id、scheduled_cutoff、cohort、host、start/end、status；唯一键(asset,cutoff,cohort,purpose)控制重复调度 |
| `raw_payloads` | content_hash、provider、redacted_request、bytes/blob位置、schema、fetch_time；不存API Key；引用对象随备份保留 |
| `observations` | 第3节完整时间/血缘/单位契约；同原始记录修订新增revision，禁止覆盖 |
| `evidence_snapshots` | snapshot_id、cutoff、observations有序引用、missing清单、完整性、hash；seal后不可更新 |
| `factor_values` | snapshot、asset、horizon、factor_id、输入引用、window、raw_value、transform、历史mean/std/percentile、normalizer_state_hash、context_score、predictive_score、theta/eta、budget/alpha/Q、contribution、status/reason |
| `predictions` | prediction_id、snapshot_id、model_version、issued_at、E、regime连续值/标签、directional/evidence/edge状态、support/conflict/missing引用、完整冻结报告、hash |
| `evaluation_jobs` | prediction、evaluation_spec_id、目标时间规则、pending/due/retry记录；可变队列是执行状态，不能改变冻结预测 |
| `outcome_observations` | prediction、baseline/endpoint价格来源/时间/偏差、return、label、evaluation_version、assessed_at、supersedes_id；一次结果修正=新记录 |
| `calibration_reports` | cutoff、包含的prediction与outcome版本hash、统计、分组样本、候选建议、拒绝原因；不可覆盖 |
| `research_trials` | 假设、预注册时间、单一变量、基线、主指标、数据分割、试验总次数、sealed样本开启日志、结果（包括NONE） |
| `annotations` | 可选AI/人工解释、模型/提示版本、被引用预测ID、生成时间；不得成为原预测的事后改写 |

同一asset/cutoff/horizon/model_version最多一条正式prediction；重复触发返回既有ID。中途失败的partial run与已完成冻结分开；恢复时复用同一sealed snapshot，不能重抓新数据却沿用旧cutoff。

冻结在一次SQLite事务内完成；FOREIGN KEY、唯一约束和针对sealed表的UPDATE/DELETE拒绝触发器共同约束。代码之外有数据库所有权的人仍能篡改，所以不能声称密码学不可篡改。canonical JSON（UTF-8、排序键、固定float序列化、禁NaN）生成SHA-256，日清单hash链接前日并导出独立备份，提供篡改可检测性。

浮点可复现要求：固定Python/数值库版本与依赖锁、输入顺序、缺失处理、ddof、时区库和优化器参数；同环境要求hash一致，跨平台数值检查容差1e-10并记录差别。随机自助法保存seed。原始载荷不允许凭模型升级删除；许可不允许保存的源不适合严格可重放主链。

## 10. Outcome Evaluation：程序判断是否兑现

主目标是标的参考价格变化，不是策略P&L。没有订单、费用、换仓和执行模型，就不报告Sharpe、盈利率或可交易收益。未来交易研究须另立契约并按项目要求独立验证。

```
R_h = log(P_endpoint/P_baseline)
sigma_hat_h = 在cutoff前估计的同cohort、同horizon收益标准差
delta_h = max(2×spread_fraction_at_cutoff, 0.25×sigma_hat_h)
Y = Up if R_h>delta_h; Down if R_h<-delta_h; Flat otherwise
```

sigma_hat优先用最近252个已兑现、同cohort horizon收益（最低126）；H4先不足则可用审计合格小时历史构造相同截点的4H样本。日频启动时可使用 `RV20/sqrt(A)×sqrt(h)` 作为明确的近似分支，须单独evaluation版本；H4没有小时数据时不从日线硬推。只有reference_last无spread时使用事前登记的最小噪声阈值，不填写0：初始10bp（Gold/BTC）或2bp（DXY/EURUSD）是待敏感性检验的研究参数。

阈值只在cutoff计算并冻结。市场波动很大时，1bp同向变动不能算强兑现；Flat不从准确率分母悄悄删除。

需要分别统计：

| 指标 | 精确分母/算法 |
|---|---|
| Schedule coverage | 成功冻结的正式预测数 / 应运行的资产×截点×期限数 |
| Data coverage | 满足输入门槛数 / 正式预测数；另列每叶可用率 |
| Outcome coverage | 已成功评价数 / 已到期且应可评价数；closed与missing单列 |
| Candidate coverage | Candidate或Validated数 / 正式预测数，按发出时标签；缺数据导致弃权仍在分母 |
| Validated edge coverage | 发出时Validated数 / 正式预测数；尚未认证阶段为0，不能后来追认历史标签 |
| Edge hit rate | 已评价且发出时有指定Edge标签、方向与Up/Down一致数 / 同集合全部已评价数；Flat算未命中 |
| 三分类准确率与全机会命中占比 | Positive→Up、Negative→Down、Neutral→Flat；三分类准确率分母为已评价且directional_view非null的记录，同时报告该集合/全部已评价机会。另报命中数/全部已评价机会；null是弃权，不能当正确Neutral或被隐去 |
| Balanced accuracy / confusion matrix | 各真实类别recall的均值及3×3计数；类别缺失时不强算完整指标 |
| False positives | 发出方向但实际反向或Flat；分别报告，不混成一个“错” |
| Rank IC | 每资产×期限沿时间计算Spearman(E,R_h)；不是四个资产同日的横截面IC |
| Signed normalized outcome | mean(sign(E)×R_h/sigma_hat_h) on predefined edge cohort；不是净交易收益 |
| Selective risk | 在预注册阈值集合{.20,.35,.50,.75}上的错误率—coverage曲线；正式阈值固定，不从测试集挑最好点 |
| Abstention audit | Neutral/Mixed/NoClearDriver/NoEdge/缺数据分别计数，列出弃权期的结果分布 |

No Edge是决策状态，不是一个可用价格回看证明“正确”的事件；Neutral则可以用Flat标签评价。两者不可混为“没跌所以中性预测成功”。

### 10.1 Probability Calibration 的边界

E不线性映射到百分比。初版 probability=null。足够样本后可以训练三分类ordinal/logistic校准层，并在独立时间外数据上评价multiclass Brier、log loss、可靠性曲线和分箱样本数；`pUp+pFlat+pDown=1`。预测概率当时冻结，后来校准版本只影响新判断。

用相同数据拟合概率与报告Brier属于泄漏。至少200个有效独立OOS样本、每类至少30，且另有未使用验证块后才允许候选校准器；样本不足显示不可校准。区间估计用时间块bootstrap，禁止将2tanh的输出叫“置信概率”。

### 10.2 解释价值和预测价值的独立评价

- 解释模型：冻结beta后，比较下一时期对“同期已发生收益”的残差、MAE及解释方差；只标统计解释，不声称因果。
- 预测模型：冻结theta后，预测未来R_h；与零收益/随机游走、历史多数类、同覆盖随机发声和简单趋势基线比较。
- 因子贡献图表示模型计算归因；删除因子后性能变化才是增量信息证据。二者都不能证明经济因果。

## 11. Slow Calibration 与版本治理

每天采集与补评；每周生成数据健康和描述统计；每月在固定截止点生成Calibration Report。未达门槛也生成“样本不足”的报告，不产生自动参数修改。

### 11.1 样本量与依赖

每天的D5结果高度重叠，一年250次预测不等于250个独立5D实验。报告N_raw、不同日期数、非重叠样本数与N_eff。可用 `N/(1+2×sum_positive_autocorr)` 作为诊断估计（滞后上限预注册为20），不得当精确样本数；保守门槛同时要求非重叠计数。

不跨资产合并命中率假装扩大单资产样本。四个horizon同日共享信息，不能相加成四倍独立样本。主要置信区间用按日成块的bootstrap（块长至少5个有效日；候选10/20日用于稳健性）；按资产、期限分别计算。时间序列回归推断可用HAC，不能用独立样本二项检验代替。

建议初始门槛：

| 用途 | 最低门槛（必要但不充分） |
|---|---|
| 展示滚动表现 | 30个已评价不同日期；仍标描述统计 |
| 一般权重/函数候选 | N_raw>=250、非重叠样本>=100、至少12个月跨不同状态；历史PIT合格数据可参与 |
| 单独regime系数 | 每个状态N_eff>=100且至少50个非重叠结果，否则使用pooled系数或0 |
| 发布Validated Edge | 锁定规则后的OOS/forward样本N_eff>=100、有Edge的N_eff>=50、覆盖率>=10%、不同时间块方向一致，并优于基线；同时通过数据完整性门槛 |
| 概率校准候选 | 见10.1；独立的校准训练与验证数据 |

数月运行通常足够暴露数据问题、获得初步统计，但不足以证明四资产×四期限×多个regime都可靠。尤其月度CPI与周频COT不能靠前向填充制造大量独立冲击。报告事件独立次数和COT独立发布次数。

### 11.2 Walk-forward 与防过拟合

1. 每次研究先登记问题、理论符号、证伪条件、原模型、唯一主要改动、主指标和停止条件。
2. 有足够历史时使用滚动/扩展训练（起始3年）、验证（6个月）、测试（下一3个月）；历史不足可缩小研究范围，但不能把同一块既调参又验收。
3. 切分依据预测/结果时间：凡训练标签区间与验证/测试区间重叠的样本都purge；跨边界再留至少最大horizon的gap。标准化规则、聚类、残差回归系数和regime阈值的选择只用训练数据。部署算法规定每日更新的滚动Z/percentile可以在测试回放中读取截至该时刻已知的先前观测，不能读取当前冲击自身、未来观测或未兑现标签；必须与live完全相同，不用整段测试集重新拟合尺度。
4. sealed末段在公式、数据口径与候选选择冻结后才打开。打开行为登记；看过后它不再是新模型的未见样本。
5. 每月优先只提出一个家族或公式改动；不自动全因子大网格搜索。累计试验数、失败与零结果一并保存。多重候选检验使用预注册Holm校正或控制FDR，不能只报赢家。
6. 比较基线和候选须用相同日、相同数据和评价契约；报告共同覆盖与全日覆盖。特征缺失更少带来的增益与模型预测增益分开。
7. 候选在独立forward shadow运行至少一个完整月后再评审；一个月仅验证运行与明显失配，不替代上面的统计样本门槛。

### 11.3 消融与数据源价值

每个家族同时做两种消融：冻结其他系数、将该块置零以测计算依赖；按同样训练规则移除该块重训，以测可替代的独立信息。删除DXY但保留其几乎等价派生指标，不能宣称DXY没用。

来源消融先按lineage合并。比较数据时效、缺失率、不同来源误差以及前瞻指标；同一上游多包装不会增加经济证据。MA、动量、斜率先测整个trend cluster，再测各叶增量；nominal/real/breakeven以及DXY/EURUSD也需组消融。

Calibration Report固定内容：样本与缺失审计、accuracy/coverage曲线、每asset/horizon/regime指标及区间、系数跨折符号稳定性、家族增量、异常日归因、数据源边际贡献、试验总数、候选参数差异、接受或NONE结论。

### 11.4 Model Manifest 与晋级

命名示例：`Gold.GCProxy.D3.v1.0.0`与`Gold.XAUUSD.D3.v1.0.0`是不同模型族。版本内冻结：leaf列表、输入源、单位、日界、窗口、Z/RZ/percentile、先验/回归系数、预算、门控、regime、标签阈值、校准器、评价契约、训练数据截止及hash、代码/依赖hash。

- 改标的、结果定义或horizon时升级major/模型族，准确率不能直接拼接。
- 改权重、公式、交互或输入源时升级minor；例 Gold V1→V1.1。历史不重写。
- 修报告格式等不影响数字的改动可patch；任何影响数值的bug修复生成新预测版本和明确的历史修订研究，不覆盖live。
- 候选晋级必须有接受记录；自动化只生成报告和candidate，不自行切换生产权重。AI可以提出改进理由，无权改已冻结参数。

主验收指标预先选定为“相同或更高coverage下的方向错误率降低”，附块bootstrap区间；Signed normalized outcome和rank IC为次指标。若Coverage不足10%、只在一个月份有效、或增益区间含0，则不认定更好，继续shadow或返回NONE。

## 12. 独立运行、报告和模型解释视图

```mermaid
flowchart LR
  S[Windows Task Scheduler] --> P[Python Pipeline]
  P --> D[现有与增量 Provider]
  D --> Q[时间与单位校验]
  Q --> F[确定性因子与分期限模型]
  F --> L[SQLite 冻结账本]
  L --> O[到期结果评价]
  O --> C[慢校准报告与候选版本]
  L --> UI[现有六模块与因子树视图]
  L --> AI[可选 DeepSeek 研究注释]
  AI --> UI
```

未来CLI建议为collect、freeze、evaluate-due、calibration-report、serve等独立子命令；这里仅是接口设计，本轮不创建代码或任务。Windows调度器每5分钟运行短生命周期dispatcher，由zoneinfo判断纽约08:00与到期时间，避免把固定北京时间当作全年纽约时间。进程锁/SQLite lease防重入，失败指数退避，有总超时和逐源错误记录。

运行不依赖Codex，也不依赖模型API。电脑关机或无网仍会中断本地采集；必须显示missed run。Windows可设置登录前运行、唤醒、错过后补执行；要真正24/7则将相同pipeline迁到常开主机。未来部署改变不能消除本地硬件离线这一事实。

六模块映射：Event Risk显示事件与不确定性；USD显示美元及EUR两侧差异；Rates显示名义/实际/利差；Equities显示股市及共同风险；Volatility显示ATR/RV/VIX/IV；Target-specific显示该资产Evidence Score、各horizon状态及特异因子。统一快照和时间语义作为兼容入口，原报告不需要推翻。

这里指现有Skill/README的六模块，不误称为当前六张卡片的一一字段映射：Web `regime`实际字段是eventRisk/usd/rates/riskAppetite/volatility/consistency，目标背景另在assetBackgrounds中。最小迁移保留这些字段和卡片，将因子解释视图及确定性结果作为独立附加对象/页签，不把consistency卡强行替换成交易方向卡。

新增模型解释视图：

```
Gold / D3 / v1.0 / cutoff时间 / provisional
  └─ 利率与美元（预算 .40，使用 .xx，缺口…）
      └─ 10Y Real Yield（G.RY）
          ├─ Source：Treasury real curve 10Y；原始观察ID/链接
          ├─ Value：2.10%；观测日期/发布时间/接收时间
          ├─ Transform：5D差10bp；历史均值0、标准差8、z=1.25
          ├─ Context Score：-1.3645
          ├─ Predictive Score：-.4107；theta/eta及训练截止
          ├─ Weight：family .40 × leaf .60 × Q 1
          ├─ Contribution：-.0986
          └─ Validation：样本量、外样本IC、消融、状态
```

树里显示null与disabled，不自动折叠掉不利证据。分数能相加核对，所有子节点贡献和必须等于父节点。鼠标点击公式可见具体参数；切换horizon时切换真正模型，不能只是换标题。默认页面展示最新冻结run；新采集快照不能混入旧报告数字。

Performance Dashboard按asset→horizon→model_version→cohort→regime筛选，同时展示上面的coverage各分母、accuracy/区间、数据源失败与样本不足。更新到下一版本时保留旧版本同期shadow曲线。

AI研究员只读取冻结事实、分数和引用，输出独立注释：关系解释、冲突可能原因、待验证假设。程序验证其数值与引用；LLM失败时用确定性摘要直接完成报告。AI解释不能更改分数、标签、结果或日程。

## 13. 从当前项目最小迁移

| 阶段 | 增量位置 | 可审查的完成条件 |
|---|---|---|
| A 数据契约与账本 | 在现有Provider之上加normalization/store；保留intraday.py兼容输出 | as-of、UTC/DST、零值/缺失、重复运行和冻结不可覆盖可重放 |
| B 研究标的与历史 | 复用Yahoo/Treasury，增FRED/ECB；审计Gold现货/期货、小时历史、CFTC类别 | 每源有真实覆盖矩阵、最大缺口、发布/修订策略；不虚构warmup |
| C 确定性模型 | 新增factor registry、scoring、regime；按目录启用小核心 | 合成输入变化对分数的影响可复现；同载荷同manifest输出一致 |
| D 自动评价与调度 | Python CLI、SQLite outcome queue、Windows任务安装说明/脚本 | 无Codex登录、无AI Key仍能采集→冻结→到期评价；重启不重复 |
| E 解释视图 | 现有web加ledger只读接口与树；Codex SDK变可选注释后端 | 四资产四期限可追到叶子来源和公式；旧六模块仍工作 |
| F 慢校准 | 统计报告与candidate manifest | 有效样本、purge、baseline、消融和NONE；不能自动覆盖版本 |

架构建议模块：`evidence.py`、`storage.py`、`factors/`、`models/`、`evaluation/`、`calibration/`、`scripts/oracle_pipeline.py`。是候选职责边界，不是要求照此拆大量文件。Provider和依赖注入/Fake HTTP测试模式继续复用；不引入OpenBB全栈替换已有适配层。

必要新增投入依次是价格契约/历史、事件日历、ECB/FRED、长期衍生品归档。官方事件日历可先补“什么时候发布”；BLS提供iCal，但不能因此得到市场consensus。完整consensus与Gold/FX期权历史可能需要付费，实施前列出具体源和缺口，不预设已取得。[BLS 日历](https://www.bls.gov/help/hlpiCAL.htm)

本轮只生成文档；没有注册Windows任务、安装包、生成数据库、改模型边界或进行权重估计。

## 14. 预注册的首批验证与研究者修改入口

| 假设 | 唯一主要变化 | 证伪条件 |
|---|---|---|
| Gold实际利率有未来增量 | 趋势基线→增加滞后10Y real变化 | OOS无改善、符号不稳定、仅同期解释有效，则预测权重0 |
| EURUSD双侧利差优于美元反向代理 | 同一趋势基线分别加入双侧利差或DXY ex-EUR | 无增量则保留背景，不把EUR当DXY翻转 |
| BTC衍生品提供独立信息 | 控制趋势/DXY/risk后只加入funding block | 表现仅来自同日price或名义OI估值变化，则拒绝 |
| USD risk作用依赖状态 | 主效应基线→增加一个stress交互 | 样本不足或purged OOS不改善，则eta=0 |
| 完整树优于小模型 | 同数据、同日期比较稀疏模型与扩展模型 | coverage下降且错误率无改善，返回小模型 |

所有试验停止条件是达到预注册数据截止与样本门槛后完成一次评估，允许NONE；不继续搜索直到显著。本轮没有运行上述试验。

研究者最值得先质疑的五处：Gold评价标的是现货还是期货代理；纽约08:00是否符合实际使用；方向阈值.35与Flat阈值.25sigma是否合适；弱理论先验是否值得保留；哪些家族足以值得付费获得PIT数据。修改这些均应先改规格/manifest，再开始验证，不改过去账本。

## 15. 一手依据与证据边界

- [Chicago Fed：What Drives Gold Prices?](https://www.chicagofed.org/publications/chicago-fed-letter/2021/464)：支持把实际利率、通胀预期、宏观悲观分开研究；其历史尺度和利率代理不同于本规格，不提供本规格4H/5D权重。
- [BIS：Crypto carry](https://www.bis.org/publications/working-paper-1087-crypto-carry)：支持研究基差、杠杆需求和尾部风险；不能推出“高funding明日必跌”。
- [ECB：Why is it so difficult to beat the random walk forecast of exchange rates?](https://www.ecb.europa.eu/pub/pdf/scpwps/ecbwp088.pdf)：提醒短期汇率必须面对随机游走基线，长期关系不能直接移植至4H。
- [ECB收益率曲线](https://www.ecb.europa.eu/stats/financial_markets_and_interest_rates/euro_area_yield_curves/html/index.en.html)：区分zero/forward/par以及AAA/all issuers，模型拟合曲线不等于德国国债或OIS。
- [FRED Real-Time Periods](https://fred.stlouisfed.org/docs/api/fred/realtime_period.html)：宏观修订和PIT时间契约。
- [CFTC COT说明](https://www.cftc.gov/es/node/128971)：报告类别及发布滞后；不同类别不能混用。
- [Deribit Funding历史](https://docs.deribit.com/api-reference/market-data/public-get_funding_rate_history)：可请求小时历史及interest_1h/interest_8h；项目尚未封装该方法。
- [ICE DXY方法](https://www.ice.com/publicdocs/data/ICE_FX_Indexes_Methodology.pdf)：固定篮子与EUR重叠处理。

上述资料支持变量定义与研究动机；本规格的预算、tanh尺度、阈值和样本门槛是设计提案。没有引用能替代本项目自己的PIT数据、时间外测试和长期账本。
