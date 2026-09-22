[English](README.en.md) | **中文**

# Digital Oracle 📈

Digital Oracle 是一款让 AI Agent 基于金融市场数据研究长期问题和盘前市场背景的开源 Skill。

适用于 OpenClaw / Claude Code / Cursor / Codex。

我们生活在一个噪音极度泛滥的时代。社交媒体上充斥着情绪化的预测 — 有人说房价要崩了，有人说黄金要上天，有人说明天就打仗。这些观点往往顺应人群情绪，而不是基于客观数据的理性分析。

但交易数据不一样。

价格是绝对理性的 — 当一个人要把自己的钱押在某个结果上时，他会比发一条短视频认真很多。

这就是有效市场理论的核心洞察：**所有公开信息都已经被价格消化了。一切信息都在 K 线里。**

Digital Oracle 把这个洞察变成了一个可执行的工具。它接入了多个金融数据源 — **从 Polymarket 和 Kalshi 这样的预测市场，到美国国债收益率曲线、CFTC 机构持仓、SEC 内部人交易、各国央行利率、加密衍生品，以及 A 股的拆单资金流与板块轮动。**

它不看报纸不读新闻，不消费文章、短视频、播客，只通过从金融数据中挖掘出的价值信号，来回答房价涨跌、黄金走势、比特币周期、军事冲突概率这类问题，并给出结构化的概率估计和推理链。

某种意义上，这就是新时代的数字先知。

## 能回答什么问题？

- "WW3 的概率是多少？"
- "中国房价还会跌多久？"
- "AI 是不是泡沫？"
- "现在适合买黄金吗？"
- "比特币到底了吗？"
- "NVDA 期权溢价是不是太高了？"

只要有市场在定价这件事，Digital Oracle 就能给出一个基于交易数据的概率估计。

## 数据源

| Provider | 数据类型 | 用途 |
|----------|---------|------|
| Polymarket | 预测市场合约 | 事件概率定价 |
| Kalshi | SEC 监管二元合约 | 美国政治/经济事件 |
| Stooq | 股票/ETF/外汇/商品 | 价格历史和趋势 |
| Deribit | 加密衍生品 | 期货 term structure、期权 IV |
| US Treasury | 国债收益率 | 利率曲线、通胀预期 |
| CFTC COT | 期货持仓 | 机构仓位方向（smart money） |
| CoinGecko | 加密现货 | BTC/ETH 价格、市值 |
| SEC EDGAR | 内部人交易 | Form 4 买卖信号 |
| BIS | 央行数据 | 政策利率、信贷/GDP 缺口 |
| World Bank | 发展指标 | GDP、人口、贸易 |
| Yahoo Finance | US 期权链 | IV、Greeks、put/call ratio |
| Eastmoney | A 股行情与资金流 | 个股/ETF 行情、K 线、拆单量级资金流、板块轮动 |
| Web Search | 网页搜索 | VIX、CDS 等补充数据 |
| Yahoo Market Core | 盘前跨市场快照 | DXY、ES、NQ、VIX、Gold、FX、BTC/ETH；保留市场时间与新鲜度 |
| Trading Economics Calendar | 结构化经济日历 | 中高影响事件、Actual/Forecast/Previous（需 API key） |

原有 Provider 保持原来的认证要求。盘前经济日历使用 Trading Economics 正式结构化 API，需要设置个人 API key；未配置时系统会明确降级，不会抓取未经授权的财经网页。

## 日内盘前 Market Context

新版增加了一个独立但不取代原能力的盘前模式：

```text
用户选择市场 / 提出问题
        ↓
Codex 识别目标与时段
        ↓
经济事件 + 全球市场核心
DXY / US2Y / US10Y / ES / NQ / VIX
        ↓
目标市场专属数据
Gold / FX / BTC·ETH·Deribit
        ↓
Signal Routing 信号路由
相关性 / 时间匹配 / 信息增量
        ↓
Codex 跨市场确认、驱动与背离分析
        ↓
简洁 Market Context + Web UI
```

固定六模块是 Event Risk、USD、Rates、Equities、Volatility、Target-specific。这个模式只回答“今天盘前市场正在定价什么”，不分析分钟K线形态，不输出交易方向、入场、止损、目标位或日内涨跌概率。完整方法见 [盘前 Skill](skills/intraday-market-context/SKILL.md)。

### 数据时间与新鲜度

盘前快照统一提供 `generated_at`、`session_date`、`session_timezone`、`market_time`、`fetched_at`、`previous_close`、`since_previous_close_pct`、`today_change_pct` 和 `freshness`（`fresh / delayed / stale / unknown`）。“当日”按所选会话时区计算，不隐式沿用服务器本地日期。

经济事件时间固定为 UTC，并保留 `time_precision`（`exact / estimated / unknown`）；网页明确转换为 UTC+8 展示，估计发布时间不会伪装成精确时刻。

US 2Y、US 10Y 和 US 10Y Real Yield 使用美国财政部官方日频曲线，因此明确标记为慢背景，不冒充实时收益率。DXY、ES、NQ、VIX 和目标资产沿用项目已有的 Yahoo 数据路线，并新增时间戳和新鲜度。Crypto 的 Funding/OI/Basis 复用 Deribit 官方公共 API。

### 测试原始盘前数据

```bash
python scripts/intraday_snapshot.py --target gold --pretty
python scripts/intraday_snapshot.py --target eurusd --pretty
python scripts/intraday_snapshot.py --target btc --pretty
```

支持目标：`global`、`equities`、`gold`、`eurusd`、`gbpusd`、`usdjpy`、`audusd`、`btc`、`eth`、`crypto`。

### 启动本地网页

前置条件：Node.js 18+、Python 3.10+，以及可用的 Codex 登录会话或 `CODEX_API_KEY`。官方 Codex SDK 只运行在服务端，浏览器不会接触密钥。

```powershell
# 可选但推荐：启用正式经济日历
$env:TRADING_ECONOMICS_API_KEY="你的 Trading Economics API key"
$env:PYTHON_COMMAND="python"

cd web
npm install
npm start
```

打开 `http://localhost:3000`。网页包含市场选择、六张环境卡片、跨市场数据、新鲜度、今日事件、市场正在定价什么、关键背离、各资产背景和 Ask Oracle。`POST /api/analyze` 先让 Provider 层生成带时间语义的统一快照，再启动或恢复官方 Codex SDK Thread；Codex 在只读模式下选择相关信号、解释确认与背离，不由网页端固定规则代替分析。默认超时为 360 秒，可用 `CODEX_TIMEOUT_MS` 调整。

## 安装

### OpenClaw

```bash
clawhub install digital-oracle
```

### 其他 AI Agent（Claude Code / Cursor / Codex / ...）

直接告诉你的 Agent：

> 安装这个开源项目并读取 SKILL.md 作为你的工作指令：https://github.com/komako-workshop/digital-oracle

Agent 会自行 clone 代码、阅读方法论、调用 provider。

### 前置依赖

- [uv](https://docs.astral.sh/uv/) — Python 包管理器，skill 运行时用它执行 Python 脚本
- 核心 Provider 优先使用 Python 标准库。只有原有期权链分析需要额外安装：

```bash
uv pip install yfinance
```

## 原有长周期 Skill 的工作原理

> 本节保留原有通用 Provider + Agent 框架，不适用于上面的盘前 Market Context Skill。

1. **理解问题** — 拆解核心变量、时间窗口、可定价性
2. **选择信号** — 根据问题类型选择 3+ 个独立数据源
3. **并行拉取** — 用 `gather()` 同时调用多个 provider
4. **矛盾推理** — 找不同市场之间的分歧，解释为什么它们可以同时正确
5. **输出报告** — 结构化的多层信号表格 + 概率估计 + 场景分析

## 项目结构

```
digital-oracle/
├── SKILL.md                # Skill 定义（OpenClaw 读取这个文件）
├── AGENTS.md               # Codex 长周期/盘前任务路由与边界
├── skills/
│   └── intraday-market-context/ # 盘前 Market Context Skill
├── digital_oracle/         # Python 源码
│   ├── concurrent.py       # 并行执行工具
│   ├── http.py             # HTTP 客户端抽象
│   ├── snapshots.py        # HTTP 响应录制/回放（测试用）
│   └── providers/          # 可组合的数据 Provider
├── references/             # API 速查
│   ├── providers.md        # Provider API 参考
│   └── symbols.md          # 交易符号目录
├── scripts/                # Demo 脚本
├── web/                    # localhost Web UI + server-side Codex SDK
└── tests/                  # 单元测试 + fixtures
```

## 设计原则

- **零依赖优先** — 大多数 Provider 只用 Python 标准库，无需 `pip install`
- **依赖注入** — 所有 provider 接受可选的 `http_client` 参数，方便测试
- **部分失败容忍** — 一个数据源挂了不影响其他结果
- **快照测试** — 录制真实 HTTP 响应，CI 里无网络也能跑测试

## Gold Asset Workbench · G001

首个可运行资产研究模型已经加入，保留上述盘前工作流。Gold使用明确标识的GC Proxy，不能冒称XAUUSD。无需Codex或模型API即可完成采集、确定性计算、冻结、结果回看和页面读取。

```powershell
python -m pip install -r requirements-gold.txt
python scripts/asset_pipeline.py daily
powershell -NoProfile -File scripts/start_gold_workbench.ps1
```

首次初始化及调度见[运行手册](docs/GOLD_RUNBOOK.md)。页面默认[Gold工作台](http://127.0.0.1:3012/asset.html?asset=gold)；现有Node服务亦可直接访问`/asset.html?asset=gold`。

- [所有资产必须遵循的通用研究协议](docs/UNIVERSAL_ASSET_RESEARCH_CONTRACT.md)
- [Gold实验预注册](docs/GOLD_EXPERIMENT_PROTOCOL.md)
- [Gold研究员手册与真实OOS结果](docs/GOLD_RESEARCH_HANDBOOK.md)

首轮结论：没有已认证Edge。D1/D3/D5可以运行研究影子模型，H4明确缺数据；历史实验与live预测分账，参数不会每日自动调优。请勿将先前盘前模式的“禁止方向研究”说明误解为禁止显式请求的资产模型研发。

## License

MIT © 2026 komako-workshop — see [LICENSE](LICENSE).
