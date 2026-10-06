# Source registry / actual capability · 2026-10-06

本表区分“源连接成功”与“数据本身足够新”。官方来源仍可能停更、修订或失去公开访问；Tier 不直接作为预测权重。

## 当前实现

| 数据 | 来源 / 频率 | 使用及当前限制 |
| --- | --- | --- |
| GC=F、DXY、SPX、VIX、Brent、GLD、Silver | 既有 Yahoo 市场历史，日频，Tier2 | 本轮 12 序列 collect 全部成功；连续合约/代理/收盘时间不同。GC 不是 XAUUSD，GLD 不是资金流 |
| DFII10、DGS2、DGS10、T10YIE | 既有 FRED 官方 CSV，日频，Tier1 | 实际/名义收益率、通胀补偿；latest-vintage，无历史发布精度，不能称严格 PIT |
| COMEX Gold 管理基金净仓/OI | 既有 CFTC 官方历史，周频，Tier1 | 4 个原生周观测变化；报告观察日和公布日不同，不能把它作为日内新增冲击 |
| AUDNZD / EURUSD / USDJPY | [ECB 90日参考汇率](https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml)，日频，Tier1 | 本轮在线成功。全部欧元报价统一换算：NZD/AUD、USD、JPY/USD。非 executable spot，非分钟报价 |
| AU 现金利率目标 | RBA F1 CSV `FCMMCRTD`，日频，Tier1 | 按 Series ID 解析，测试通过；本机在线请求失败，显示 UNKNOWN，不硬编码当前现金利率 |
| NZ OCR | RBNZ B2 官方表，日频，Tier1 | 只接受明确日期与 OCR 列；本机在线 HTTP 失败，显示 UNKNOWN，不从标题猜值 |
| AU / NZ 隔夜市场利率 | FRED/OECD `IRSTCI01AUM156N` / `IRSTCI01NZM156N`，月频，Tier1 | 网络成功，但 NZ 最新停在2024-12；超过75天显示 STALE。AU 当前可用。不是央行 target 或 OIS |
| 官方事件标题 | Fed monetary RSS / RBA media RSS / ECB press RSS，事件频，Tier1 | Fed/ECB 本机成功，RBA失败。保存标题、链接、publication 与 first_seen；不假设正文已被核验 |
| 经济日历/consensus | 既有 Trading Economics Provider，Tier4 | 需 `TRADING_ECONOMICS_API_KEY` 和足够套餐权限；当前没有，MISSING。数据公布前要先连续采集冻结，后置 key 不会补出严格历史共识 |
| GitHub prior art | GitHub REST，周度 | 本轮七个仓库实际检查成功。Actions 用 github.token，CLI 可用 GH_TOKEN；失败 UNKNOWN，非“没有更新” |

生产环境网络可能与本地不同，以网页 source health 与 Actions 实际结果为准。不把本机访问失败推断为供应商永久停机。

## 缓存、新鲜度、血缘

公共宏观源固定 URL，18秒请求上限、3MB载荷上限，4线程、六小时缓存；未来数据与当日未确认观测保守排除。日频观察超过5日 STALE，CFTC超过12日，月度隔夜超过75日。当前是透明的初始阈值，尚非节假日/公布日专属 SLA。

每次读取缓存沿用原 ingestion_time，不以重抓刷新首次可用时间。失败保留最近合格缓存但标明 STALE；无缓存 UNKNOWN/MISSING。无零填充、无随机样本。公开快照含 source URL/params、原始载荷 hash、计算窗口；载荷全文保留在加密 SQLite，不公开复制有许可限制的长文。

## 待投资的数据（按研究价值排序）

1. 同事件口径的发布前 consensus、官方 actual/revision/vintage、精确 release time，加上同步 Gold/FX/2Y/real yield 事件报价。这才能检验 surprise/reaction/rejection 的增量价值。
2. 期限/时点一致的 OIS、Fed Funds futures 和 FX forwards，明确合约计价与概率转换假设，不把当前现金利差当未来 path。
3. 稳定 XAUUSD 现货与事件级历史、Gold ETF tonnes/flows、央行需求发布版本、CME期权曲面。采购前按 Universal Contract 审查费用、许可、覆盖、修订与真实增量。

本轮检查过既有 BIS policy_rates 适配器作为 AU/NZ fallback，本机请求也失败，未自动启用未验证替代源。ALFRED realtime/vintage 机制已纳入契约，但没有将 latest CSV 冒充 vintage 数据。免费公开数据不足时，保留空分支比虚构专业结论更可靠。
