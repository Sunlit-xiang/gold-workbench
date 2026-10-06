# Data / evidence / memory contracts

MEP-1.0。数据库仍为既有 SQLite；新表与 `datasets/models/predictions/outcomes` 严格分开。每条记录以 canonical JSON SHA-256 验证，触发器禁止 UPDATE/DELETE。改正只能追加新记录并解释原因，不重写过去。

## Evidence：叶节点是数据契约，不是形容词

`macro_core.Evidence` 为 frozen dataclass：

| 字段 | 规则 |
| --- | --- |
| asset / country / topic / family / layer | asset 必须注册；layer 为 structural/tactical/event/risk；国家是两国相对关系而非单边复制 |
| source / source_quality / url | Tier 1 官方，2 市场，3媒体，4聚合。等级不等于预测可靠性或可知历史 |
| observation_date | 数据描述的时期/市场观察日，不能当发布时间 |
| publication_time / event_time | 未知为 null；事件时间和文章时间分开，禁止补一个猜测时间 |
| ingestion_time / available_at | 必须带时区；可用时间不得早于首次接收或已知发布时间 |
| actual / forecast / previous / revision / units | 数值必须有限、非 bool；缺失不是 0；口径/单位必须可比较 |
| status / pit / horizon / validation | available/UNKNOWN/STALE/MISSING；当前公开 CSV 是 latest vintage、first_seen，不是 ALFRED 历史 PIT |
| raw_payload_id / transformation | 原始载荷身份；公式、lag、窗口起止、值、单位、标准化样本数/均值/标准差 |
| interpretation / stance | 经济先验，support/oppose/context/unknown；不等同收益预测 |
| independence_cluster | **去重标签**，不是已证明统计独立。名义/实际/通胀补偿共享 rates 簇 |

原始文本/结构缓存放 `macro_payloads`；标准化叶节点放 `macro_evidence`；研究网页导出不公开整份原始载荷。对重要消息目前只验证官方标题，尚无自动正文事实抽取。AI 的解释、引用和不确定性单独放 `macro_ai`，不伪装成原始事实；不提供未经校准的 confidence 百分比。

## Event → Surprise

`macro_events` 保存日历 identity、exact/date-only 精度、country、time、source reference、原始 extraction、actual、forecast、previous、revision、surprise 和被引用的共识记录 ID。

共识定义：同 event ID 与时间、同单位、发布时间之前**已保存**的最早预期；后续预期修订继续保存。发布后才拿到的 forecast 不能倒填发布前预期。模糊范围、K/M 或无法辨认的单位保持未知。`raw surprise = actual − frozen consensus`；`z = raw surprise / prior-only surprise sample std` 至少 20 个历史同口径事件。当前采集未建立完整同事件历史标准化样本，因此线上 z 多数为 null，不能展示伪造标准化强度。

previous 原始字符串保留；revision 尚不能可靠分离，保留 null，不能默认为未修订。日历是 Tier4 雷达，重大事件需核验官方正文/时间后才可进入条件因果研究。

## Pricing / Reaction / Regime

Pricing 当前保存 status、missing 与解释；没有期限/市场/时点一致的 OIS/futures/forward 曲线，不提供概率或 MOSTLY PRICED。现金利率和美债收益率不可替代这个契约。

Reaction 函数接收 `event_time + quotes(time, available_at, value, instrument, granularity_seconds)`。窗口为事件前最后报价与窗口结束后的首个报价，边界最大缺口 60 秒、报价粒度不超过 60 秒、发布前基准必须当时已知。未到期 PENDING、缺数据 MISSING、标的不同 UNKNOWN；确定性计算 `100 ln(post/pre)`，不声称因果识别。5m/30m/2h/1d 是**事件后观察窗口**，不是交易状态机。尚未接入合格实时报价，`macro_reactions` 预留且页面明确缺失，日频收盘不回填这些窗口。

Regime 分 structural/tactical/event。目前 UNKNOWN/描述性 MIXED，不从一周涨跌推断结构状态，不自动使用所谓 regime multiplier 生成方向总分。

## Snapshot / Graph / Memory

`macro_snapshots` 保存 asset/version/as_of、证据全集、支持/反对 ID、冲突 ID、pricing/reaction 状态、国家档案、数据健康、旧 dataset ID。构成可追溯的邻接图：原始载荷 → evidence → conflict/event → snapshot → AI claims。没有引入图数据库或训练类比预测器。

只读 dashboard 增加 served_at、当前陈旧标识、上一份 raw value 差异、档案索引与检索结果；不改保存的快照。`macro_workbench.py snapshot --id ...` 返回原冻结体；云端同一 ID 的 JSON 可直接查看。

检索相关性 `exp(−ln(2) × age_days / half_life)`；event/risk 3天、tactical 10天、structural 180天是检索先验，非交易权重。官方新闻按 publication age，而不是每次重抓后变成新事件。原事实永不删除。当前 query_memory 是 PIT-visible topic 查询，不声称已完成 CPI 类比回报统计。

`upstream_observations` 保存每次检查；`upstream_reviews` 保存待审案例。更新检查不改冻结研究基线，不关闭待审案例。许可或安全检查 UNKNOWN 也需研究者看见。
