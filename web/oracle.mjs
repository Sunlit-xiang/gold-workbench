export const TARGETS = new Set([
  "global",
  "equities",
  "gold",
  "eurusd",
  "gbpusd",
  "usdjpy",
  "audusd",
  "btc",
  "eth",
  "crypto",
]);

export const REPORT_SCHEMA = {
  type: "object",
  properties: {
    target: { type: "string" },
    generatedAt: { type: "string" },
    headline: { type: "string" },
    regime: {
      type: "object",
      properties: {
        eventRisk: { type: "string" },
        usd: { type: "string" },
        rates: { type: "string" },
        riskAppetite: { type: "string" },
        volatility: { type: "string" },
        consistency: { type: "string" },
      },
      required: ["eventRisk", "usd", "rates", "riskAppetite", "volatility", "consistency"],
      additionalProperties: false,
    },
    whatMarketsPricing: { type: "string" },
    divergences: {
      type: "array",
      items: {
        type: "object",
        properties: {
          title: { type: "string" },
          explanation: { type: "string" },
          evidence: { type: "array", items: { type: "string" } },
        },
        required: ["title", "explanation", "evidence"],
        additionalProperties: false,
      },
    },
    events: {
      type: "array",
      items: {
        type: "object",
        properties: {
          time: { type: "string" },
          currency: { type: "string" },
          name: { type: "string" },
          importance: { type: "string" },
          actual: { type: ["string", "null"] },
          forecast: { type: ["string", "null"] },
          previous: { type: ["string", "null"] },
        },
        required: ["time", "currency", "name", "importance", "actual", "forecast", "previous"],
        additionalProperties: false,
      },
    },
    assetBackgrounds: {
      type: "array",
      items: {
        type: "object",
        properties: {
          asset: { type: "string" },
          context: { type: "string" },
        },
        required: ["asset", "context"],
        additionalProperties: false,
      },
    },
    dataQuality: {
      type: "object",
      properties: {
        status: { type: "string" },
        notes: { type: "array", items: { type: "string" } },
      },
      required: ["status", "notes"],
      additionalProperties: false,
    },
    answer: { type: "string" },
  },
  required: [
    "target",
    "generatedAt",
    "headline",
    "regime",
    "whatMarketsPricing",
    "divergences",
    "events",
    "assetBackgrounds",
    "dataQuality",
    "answer",
  ],
  additionalProperties: false,
};

const TARGET_LABELS = {
  global: "全球市场",
  equities: "美股",
  gold: "黄金",
  eurusd: "EURUSD",
  gbpusd: "GBPUSD",
  usdjpy: "USDJPY",
  audusd: "AUDUSD",
  btc: "BTC",
  eth: "ETH",
  crypto: "加密市场",
};

export function normalizeTarget(value) {
  const target = String(value || "global").trim().toLowerCase();
  if (!TARGETS.has(target)) {
    throw new Error(`unsupported target: ${target}`);
  }
  return target;
}

export function buildPrompt({ target, question = "", session = "auto", snapshot = null }) {
  const label = TARGET_LABELS[target] || target;
  const userQuestion = String(question || "").trim();
  const snapshotJson = snapshot ? JSON.stringify(snapshot) : "{}";
  return `WEB_JSON

这是一个只读的盘前 Market Context 请求。Provider 层已经采集并规范化数据，完整快照附在下方。你负责从中选择与问题相关的信号、判断独立市场是否相互确认，并解释主要驱动与背离；不要机械逐字段复述，也不要用简单多数投票。

分析对象：${label}
会话：${session}
用户问题：${userQuestion || `请生成今日${label}盘前市场背景。`}

固定覆盖六个背景模块：事件风险、美元环境、美国 2Y/10Y 利率环境、ES/NQ 风险偏好、VIX 波动环境、分析对象专属背景。先检查 generated_at、market_time、frequency、freshness、data_quality 与 errors；stale 数据不得写成实时事实，缺失数据必须影响结论置信边界。事件为空且 calendar 未配置时，不得写成“今日无重要事件”。

禁止技术形态、具体交易方向、入场、止损、止盈、目标位和日内涨跌概率。只输出符合调用方 JSON Schema 的合法 JSON，不要 Markdown 代码围栏。

盘前数据快照：
${snapshotJson}`;
}

export function parseReport(finalResponse) {
  const report = JSON.parse(finalResponse);
  if (!report || typeof report !== "object" || Array.isArray(report)) {
    throw new Error("Codex returned a non-object report");
  }
  return report;
}
