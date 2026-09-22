# Gold GC Proxy · 实验预注册 G001

登记：2026-09-17 UTC / 2026-09-18 Asia/Shanghai，查看模型表现之前。代码运行时另存该文件hash、数据hash与开封事件。只探测过接口与字段，未按结果筛选参数。

## 身份与时钟

- 资产：Yahoo GC=F，USD/oz，未审计连续合约，明确GC Proxy；GLD仅作替代代理稳健性，不当XAUUSD。
- 可用数据：2006年以来日频GC/DXY/SPX/VIX/GLD/Silver/Brent；FRED DFII10/DGS2/DGS10/T10YIE；固定CFTC 088691 Managed Money。
- 正式支持日频 `EOD_NEXT_SESSION` 研究契约：历史特征日d的次日06:00 UTC发出，基准为发出日期之后第一个有效GC日线close，结果为基准之后第1/3/5条有效日线close。故有明确等待，不假装08:00盘前即成交；H4保持数据不足。
- Yahoo日线次日06:00 UTC才允许使用；FRED观察至少滞后一个日历日、并按可得记录向后对齐；CFTC报告日保守滞后6个日历日且不能超过14日。这些仅保守重建，不证明历史修订PIT。
- live从实际issued_at之后下一日期的完整日线建立baseline，归档后追加；不将历史回填插入live预测。未知节假日导致的延迟保留在结果实际日期；超过等待上限明确unscorable，不按缺失行情缩短horizon。

## 假设与候选（停止扩展）

H1：趋势相对固定方向有增量；H2：美元/实际利率滞后冲击比纯趋势增加预测信息；H3：breakeven、风险环境、COT依次增加独立信息。任一增量在OOS置信区间含0、分段不稳定或coverage显著更差，即不支持。

六个方向特征块：趋势（20/60D标准化均值）、DXY 5D、10Y real 5D bp、10Y breakeven 5D bp、risk（VIX 5D冲击减SPX 5D收益标准化平均）、COT Managed Money净仓/OI的4周变化。nominal、curve、silver、Brent、ATR/RV/ER、252D趋势作为Context/Risk或基线，不重复加权。宏观修订量、ETF真实申赎、期货carry、期权surface和事件surprise无可靠历史契约时Disabled。

基线：永远Neutral、永远Positive、20D趋势符号、252D time-series momentum符号。候选：trend ridge；trend+美元+实际利率；依次+breakeven、+risk、+COT；full逐族移除，共11个ridge定义（去重后固定列表），不扩展网格。

标准化：日变量滚动756、最少252，均值/样本标准差严格shift1，clip±5；COT在周发布序列标准化后向日频对齐，不对日填充值拟合尺度。预测目标=未来log return / 事前RV20×sqrt(h)。Ridge alpha=10、截距、不搜索lambda；训练最近756成熟样本、至少504，月度重估。D5参数数目按独立块控制；全模型6输入+截距。系数是研究候选，不是已认证行业敏感度。

## 划分、主要指标与停止条件

- 最后252个可构造日期为sealed holdout；之前滚动OOS为development。数据下载可保存全部原始载荷，但开封前不能展示末段结果。
- 先锁定代码/候选和测试；`research --open-holdout`明确记录开封。开封后不以此次结果调权；修bug须记录、原结果保留并承认末段已见。
- 训练只用endpoint早于信号日期的成熟标签，另留5个GC观测日gap；每个h独立拟合。当前日Z只使用过去观察，不用未来分布。
- E=2*tanh(y_hat/1.5)，每叶贡献采用共同缩放使贡献精确加总E；这是注册的新研究规格，不机械继承旧任意预算。截距单独显示；禁止称E为收益率/概率。
- 方向阈值abs(E)>=.35；目标Flat阈值=max(.001,.25*sigma_h)。Flat算方向未命中；主指标D5匹配coverage的命中差与时间块bootstrap95%区间（block20，seed固定），辅以IC、分期、非重叠样本。非重叠日偏移逐一报告，不挑最优偏移。
- 不搜索最优命中率，不提供净P&L，基准价格不是可成交保证。GLD代理及GC/GLD偏离窗口仅作诊断，不事后删除亏损窗口。
- 即使统计显著，连续合约、vintage或许可未解决仍不得认证Validated Edge。首版运行模型为固定发布的research_shadow，No Edge；daily不自动重训/替换。

## 运行工程验收

真实数据成功落库；同输入复算相同；原始载荷/模型/预测/结果append-only；重复运行幂等；H4诚实禁用；live与历史分账；断网可读历史、失败有日志；无需Codex完成CLI及工作台；不可达因子有明确原因。

## G001.2 实现审计修正（非调参）

初次G001.1报告已保存，发现两个评价实现缺口后追加修正版：开发期末尾标签也必须排除跨入holdout的结果；非重叠样本须按实际baseline/endpoint区间贪心选取，不能在过滤后的行上简单每h行抽样（节假日等待可能产生同一baseline）。新增共同发声日full-vs-ablation比较。特征、系数估计、方向阈值、数据窗口和候选集合均未改变。原报告不删除；holdout已经开封，G001.2不能宣称新的独立未见样本。

holdout属于预注册的prequential walk-forward：每个截点只用已经成熟且经过gap的标签，月度更新规则事前固定；不是拿整段holdout优化参数，也不是一个固定系数贯穿整年的验证。
