# Digital Oracle — Project Status / Architecture Snapshot

## 2026-09-24 GitHub 交付增量（当前状态）

- 正式工作台：https://sunlit-xiang.github.io/gold-workbench/ 。代码：https://github.com/Sunlit-xiang/gold-workbench 。原作者 origin 保持不变；发布工作副本位于 `.delivery/repository`，采用明确文件白名单和凭据扫描。
- Gold 工作台已改成原始事实 → 数学变换/贡献 → 因子族 → 最终判断的可展开河流图。支持中英文、真实尺度参数、截距单列、H4/D1/D3/D5、六模块研究报告、账本筛选/CSV、历史基线与留出验证。
- 新 `gold_delivery.py` 只包装已冻结模型，不重训、不修改 G001 参数或历史。API 配置支持 DeepSeek、Kimi 国际/中国，临时密钥仅内存；后台自动解读使用 GitHub Secrets，默认未配置 AI 时仍完整运行确定性流程。
- GitHub Actions 工作日计划 UTC06:17 运行；2026-09-22/23 实际触发约 UTC11:36，证明调度可延迟数小时，不能承诺准点盘前。两日云端采集均成功；截至9月23日云端归档24条预测、3条到期结果，12个数据源无连接错误。这些是运行验收，不是预测优势证明。
- 状态持久化：`gold-state` Release 保存 Fernet 认证加密的 SQLite 快照，密钥只在 `ORACLE_STATE_KEY` Secret。恢复检查 SQLite 和内容 hash；失败不重置账本。公开 `ledger` 分支保存冻结预测和追加结果，防止改写或丢失历史。原始数据不作为明文网页发布。
- 同一未来区间可能对应多条周末/跨日冻结，页面另报不同区间及不重叠区间数；原始记录命中率不能冒充独立样本统计。D5是契约基准之后5个观测日，不是周线形态；Neutral不代表预测震荡。
- 本地服务仍可运行，原 `.sqlite` 留作研究副本。9月24日已停用确认为本项目的旧 `DigitalOracle-Gold-Daily` Windows任务（可恢复），以线上账本为交付权威，避免合并已分叉的本地/云端预测。网页启动任务不受影响。
- 部署和恢复详情：`docs/GOLD_GITHUB_DELIVERY.md`。GC Proxy/严格PIT/换月/H4/No Edge等研究限制仍保留。原始数据许可、长期备份容量与调度健康需要持续管理。

## 2026-09-18 实施增量（优先于下文旧快照）

Gold G001现已实现：`asset_store.py`（append-only SQLite与hash）、`providers/research_history.py`（12条输入序列，Yahoo/FRED/CFTC三类上游）、`asset_model.py`（Gold配置、34片叶节点、6个方向研究块、确定性评分）、`asset_research.py`（成熟标签walk-forward/基线/消融/块区间）、`asset_pipeline.py`（发布影子版本、冻结、到期追加和统计）。统一CLI为`scripts/asset_pipeline.py`。

新页面`web/public/asset.html`使用同一个Node服务，数据来自`GET /api/assets/gold`；资产列表为`GET /api/assets`。Codex SDK改为只在旧AI分析入口动态加载，因此Gold工作台不依赖Codex运行时。原六模块页面保留并添加工作台入口。

实际数据：约5209个GC日观测、1057期固定COMEX Gold CFTC报告；FRED利率和跨市场历史已落库。GC原始OHLC中1行异常、Brent6行异常保留标记，范围指标不使用异常范围。数据仍为latest-vintage重建，GC连续合约未完成换月审计，严格PIT/Spot/H4问题没有被掩盖。

数据库在`research_data/oracle.sqlite`（git忽略）。已存G001.1与修正后的G001.2实验报告、首个shadow模型版本和4条正式冻结记录；首次交付时尚无到期live Outcome，未把历史回填混进live。G001.2修复开发期跨holdout标签及非重叠计数，未调阈值追求命中率。结果见[研究员手册](docs/GOLD_RESEARCH_HANDBOOK.md)。

当前本地服务`http://127.0.0.1:3012/asset.html?asset=gold`已启动并浏览器核验；没有发布公网。Windows任务`DigitalOracle-Gold-Daily`已注册为北京时间14:10运行，独立于Codex，要求Windows用户已登录。执行日志与部署限制见[运行手册](docs/GOLD_RUNBOOK.md)。

每日任务已实际烟测，LastTaskResult=0；`DigitalOracle-Gold-Workbench`已注册在Windows登录时启动网页。导出位于`research_data/exports/G001.2/`，一致性备份为`research_data/backups/oracle-20260918.sqlite`。新增单条预测只读API能读取旧版本完整冻结因子树，而不只显示当前模型。

测试：264个Python测试和5个Node测试通过；新增测试覆盖因果标准化、未来扰动、append-only、幂等、GC合约身份、缺失值、baseline时刻、合成到期闭环与无AI Web路由。浏览器已验证期限卡、模型选择、验证表和账本对话框。工程测试不等于预测有效性认证。

新增底层规则：[Universal Asset Research Contract](docs/UNIVERSAL_ASSET_RESEARCH_CONTRACT.md)，由AGENTS引用。每日任务不会重训/替换模型；任一参数升级必须明确发布新版本。未来资产复用账本/评价/页面形态，但各资产仍须实现并注册自己的数据和因子配置，不能复制Gold系数。

---

以下为2026-09-17设计阶段原始快照，保留作历史对照；其中“尚未实现”状态已由上方增量更新，不代表当前功能缺失。

快照日期：2026-09-17。项目目录：`F:\Codex_project\trader\background_engine\digital-oracle`。

用途：为研究者和下一轮开发提供可核对的现状、约束和迁移入口。本文区分代码中已实现的功能、尚待验证的数据能力和V2设计；不是部署成功证明，也不是模型有效性报告。

## 1. 本轮交付与当前定位

本轮只新增研究设计文档，没有修改Python/JavaScript运行代码、依赖、密钥、数据库或系统调度任务。

- [V2资产判断说明书](docs/V2_FACTOR_MODEL_SPECIFICATION.md)：时点契约、标准化、分期限模型、聚合、账本、结果评价、慢校准、版本和迁移设计。
- [四资产Factor Tree与叶节点目录](docs/V2_ASSET_FACTOR_CATALOG.md)：USD/DXY、EURUSD、Gold、BTC的树、数据终点、频率、公式、权重和禁用条件。
- 本文件：当前架构及缺口，供实施前复核。

当前代码定位仍是Provider驱动的盘前Market Context工作台；V2目标是保持六模块展示的可解释多资产研究系统。最新用户需求允许技术因子与4H/1D/3D/5D方向研究，但不包括交易执行、入场路径或5分钟交易状态机。

仓库审计时HEAD为 `a63e4c19a2f3313d54914c44666febaf5ffb9d6f`；工作区不是干净状态：既有README、Skill、导出文件等修改，以及intraday、Web、测试等未跟踪文件均已存在。这个commit不能单独代表工作区全部功能。未对既有改动执行覆盖、清理或提交。

## 2. 当前真实运行链路

```text
Browser: web/public/index.html + app.js + styles.css
    │
    ├─ GET /api/health
    ├─ GET /api/snapshot
    │      └─ web/server.mjs → Python子进程
    │              └─ scripts/intraday_snapshot.py
    │                      └─ IntradayMarketContextService
    │                              ├─ YahooMarketCoreProvider
    │                              ├─ USTreasuryProvider
    │                              ├─ TradingEconomicsCalendarProvider
    │                              └─ DeribitProvider（相关资产）
    │
    └─ POST /api/analyze
           ├─ 先生成同一类Python数据快照
           └─ Codex SDK Thread + web/oracle.mjs提示/JSON Schema
                   └─ 六张环境卡、事件、背离、资产背景、Ask Oracle
```

快照获取不要求LLM参与；当前完整研究解释路径确实依赖Codex SDK，并非已经实现DeepSeek可替换的独立Python量化pipeline。Web服务不等于后台日采集、不可变账本或自动结果验证。

### 2.1 关键代码入口

| 位置 | 当前职责 | V2尽量保留什么 |
|---|---|---|
| `digital_oracle/providers/base.py` | SignalProvider、metadata和异常类型 | Provider边界、依赖注入与统一异常 |
| `digital_oracle/http.py` | JSON/text HTTP、超时重试 | 传输层能力；在上层补证据时间与持久化 |
| `digital_oracle/cache.py`、`proxy_pool.py`、`concurrent.py` | 缓存、代理池、并发请求 | 继续作为采集设施，不当研究数据库 |
| `digital_oracle/intraday.py` | 组装PremarketDataBundle和数据质量 | 兼容原快照输出；把新计算结果作为附加对象 |
| `scripts/intraday_snapshot.py` | 当前盘前数据CLI | 保留为手动入口，未来调度器调用独立pipeline |
| `digital_oracle/snapshots.py` | HTTP测试录放/回归支持 | 保留测试职责，不能当Prediction Ledger |
| `web/server.mjs` | Node HTTP、Python子进程、Codex调用 | 保留页面/API骨架，未来读取已冻结结果 |
| `web/oracle.mjs` | 目标路由、提示、报告Schema | 保留六模块语义，约束AI引用冻结证据 |
| `web/public/` | 原生HTML/CSS/JS界面 | 新增树形解释/表现页签，不重做前端框架 |
| `tests/`、`web/test/` | Fake HTTP与接口/解析等测试 | 扩展PIT、缺失、重放、账本、期限与防泄漏测试 |

### 2.2 当前快照与前端契约

`PremarketDataBundle`包含schema_version、generated_at、target、session、session_date、session_timezone、core、target_specific、events、derivatives、errors、data_quality。已有市场时点、新鲜度和错误展示基础，但还没有统一的released_at/first_seen_at/vintage/lineage契约。

Skill/README定义六模块：Event Risk、USD、Rates、Equities、Volatility、Target-specific。Web六张环境卡实际使用 `eventRisk/usd/rates/riskAppetite/volatility/consistency`，目标背景在 `assetBackgrounds`。这是当前表现层的具体映射，不应为了V2评分改掉原报告主结构。

当前Web TARGETS没有独立的`usd`研究目标；DXY作为核心背景存在。V2需要添加资产研究ID/选择入口，但不必移除原有global、equities或其他FX目标。

## 3. Provider资产与真实可用边界

| Provider组 | 当前已有 | 不能误认为已有 |
|---|---|---|
| YahooMarketCore / YahooPrice / Stooq兼容 | 跨市场快照、日/周/月OHLC接口；Stooq实际委托Yahoo | 独立Stooq证据、稳定多年小时数据、许可完备的实时行情SLA |
| Treasury | 名义/实际收益率曲线、按年取数能力 | 全部发布时间/vintage已治理、利率盘中实时流 |
| TradingEconomics Calendar | 结构化事件Provider及时间精度字段 | 已配置有效授权、盘前冻结的多年consensus与首次actual库 |
| Deribit | 合约、summary、盘口、当前期权/期货相关数据 | 多年OI/期权surface库、已校验30D常期限IV/Skew、完整已结算funding历史 |
| CFTC | 商品Disaggregated Futures Only，Managed Money等类别 | EUR/BTC金融类TFF已正确接入、报告时间等于市场可知时间 |
| CoinGecko | 价格、市场及global等聚合接口 | 所有模型都保存上游更新时间、可直接回溯多年dominance |
| Polymarket / Kalshi | 事件、市场与盘口能力 | 跨合约可拼接的长期概率序列、流动性和资产相关性已验收 |
| YFinance | 通用数据与当前期权链能力 | GLD/FXE/UUP代理期权等于XAUUSD/OTC FX/DXY原生期权 |
| BIS / World Bank / EDGAR / Eastmoney / FedWatch / Fear-Greed / Web等 | 库内其他Provider适配器 | 全部进入当前盘前主链、全部具有稳定方向预测价值 |

接口存在、现场HTTP成功、结构正确、历史完整、PIT可重建、预测有效是六个不同验收层次。

### 3.1 本轮只读核查

- ECB `FM.D.U2.EUR.4F.KR.DFR.LEV`公共数据端点返回200：存款利率变化日数据可以作为新增Provider候选。
- ECB `YC.B.U2.EUR.4F.G_N_A.SV_C_YM.SR_2Y`返回200：这是AAA欧元区spot curve，不是Bund或OIS；与US Treasury par curve构造的利差只能标代理。
- CFTC `72hh-3qpy`元数据确认是Disaggregated Futures Only，不能按名称模糊匹配后当作全部金融资产的TFF数据。

这些核查未创建Provider、下载多年历史或拟合参数。具体来源和证据链接见V2目录。

## 4. 已识别的实现风险

| 风险 | 代码/数据证据 | 实施前处理 |
|---|---|---|
| Gold标的错配 | 当前目标使用`GC=F` | XAUUSD现货与GC代理分模型、分表现；审计换月与授权 |
| 历史时点精度 | Yahoo历史适配器仅d/w/m且日期化 | 小时数据独立契约；不能验证不存在的08:00→12:00历史 |
| Treasury时间和排序 | `_rate_snapshot`依赖列表首项、日期年龄与合成午夜时刻 | 日期归一排序；发布时点未知就保留未知，不伪造盘前已知 |
| 昨收语义 | MarketCore优先使用`chartPreviousClose` | 针对请求区间核验它是否符合真正前一交易日收盘；此处是待核验项，不宣称所有返回必错 |
| 缺失值被写成0 | CFTC局部整数coerce默认0 | 保留null/status，区别零持仓与未知 |
| 合约身份不稳定 | CFTC primary按日期选择最高OI行 | 固定report type、contract code与trader class |
| Basis定义错配 | 当前相对perpetual，而非spot | 新建spot basis字段；不得只改显示名称 |
| 衍生品时间错配 | 汇总时间不等于每个合约同步报价 | 保留逐腿timestamp、quote quality与期限插值输入 |
| 数据源重复 | Stooq兼容层/Yahoo；FRED转载官方源 | 保存lineage，不按Provider数量计独立证据 |
| 模型解释不可重放 | 当前由Codex选择和解释，缺少冻结数值流水 | 确定性引擎先算；AI注释独立、可缺席 |

## 5. 目前没有实现的V2能力

- SQLite研究账本、raw payload持久化与严格PIT观察表。
- 四资产完整数值因子注册表、确定性Scoring Engine与horizon-specific model。
- 不可覆盖的模型manifest、冻结预测与证据贡献链。
- 到期4H/1D/3D/5D自动评价、Accuracy/Coverage与分组置信区间。
- 慢校准、家族/来源消融、影子模型、晋级审批。
- 脱离Codex运行的完整日采集/计算/冻结/评价任务链。
- Factor Tree模型解释视图与长期Performance Dashboard。

V2规格中的初始数值均为研究先验或演示，不是从当前库里训练得到。当前没有足够证据声称某个资产、期限或regime已经具有Validated Edge。

## 6. 运行、部署与验证状态

Web `package.json`使用Node >=18、`@openai/codex-sdk`，启动入口为`node server.mjs`；端口缺省3000，可由PORT调整。Python命令来自PYTHON_COMMAND或默认python。仅记录配置机制，不记录密钥内容。

仓库存在`.openai/hosting.json`，但配置文件存在不证明有正在运行的长期生产部署。本轮没有发布站点、启动/重启服务、创建Windows计划任务，亦没有核验当前服务或外部域名的在线状态。不能保证本轮文档交付后“随时可用”。

此前审计记录Python 252项和Web 4项测试通过。本轮为文档设计，没有重新执行应用测试或以旧结果宣称新增代码通过；文档检查不等于市场数据和预测有效性验证。

## 7. 最小迁移顺序与验收

| 阶段 | 最小变更 | 先验收什么 |
|---|---|---|
| A | 现有Provider外加证据契约、SQLite与seal事务 | 时间可证明、缺失不为0、重放一致、幂等、不覆盖历史 |
| B | 资产Price Contract及合格历史；增量FRED/ECB/正确CFTC | 真实覆盖、PIT、修订、小时与日频边界、Gold代理身份 |
| C | 小核心确定性模型，完整树其余叶保留0/disabled | 合成输入算例、数值贡献闭合、重复证据约束、无AI运行 |
| D | Prediction Ledger + Outcome evaluator | cutoff/baseline/endpoint、DST/周末/节假日、漏跑与补评 |
| E | 原页面增解释与表现页签；AI仅附加注释 | 无AI仍能查看冻结判断；每贡献可追到原始数据 |
| F | 独立调度、每周健康报告、每月校准候选 | 运行不依赖Codex；统计门槛、sealed holdout、NONE合法、版本不自动替换 |

完整顺序和验收契约以[主规格](docs/V2_FACTOR_MODEL_SPECIFICATION.md)为准。A到D先形成闭环，不必等整棵树所有数据接齐，也不引入新全栈框架替换现有Provider与页面。

## 8. 下一轮实施前需由研究者确认

1. Gold先以GCProxy开始探索，还是先落实XAUUSD现货数据契约；两者不能共享认证表现。
2. 是否采用纽约08:00首个冻结cohort；日收盘研究可先验证，但不得替代盘前H4认证。
3. 接受弱先验小核心、其余节点先只显示不计方向；允许较长时间No Edge。
4. 同意初版预算、阈值和样本门槛作为待质疑的注册参数，而非宣称最佳参数。
5. 正式运行主机、数据许可与凭据供应方式另行确定；本轮未作部署承诺。

仓库祖先`F:\Codex_project\trader\AGENTS.md`要求量化研究采用quant-research流程，强调预注册、PIT与独立验证。本规格据此设置慢校准和证伪门槛。项目内旧AGENTS/盘前Skill/Web提示词仍限制方向研究，实施V2时需要明确版本化更新；本轮未改动这些运行指令。`engines/lean`不在本次范围。
