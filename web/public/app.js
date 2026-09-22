const state = { target: "global", threadId: null, snapshot: null, analyzing: false, snapshotRequest: 0 };

const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

function setText(selector, value) { $(selector).textContent = value ?? "—"; }
function formatNumber(value, unit = "") {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const number = Number(value);
  const digits = Math.abs(number) >= 1000 ? 2 : Math.abs(number) >= 10 ? 2 : 4;
  return `${number.toLocaleString("zh-CN", { maximumFractionDigits: digits })}${unit === "%" ? "%" : ""}`;
}
function formatChange(snapshot, today = false) {
  const pct = today ? snapshot.today_change_pct : snapshot.since_previous_close_pct;
  const raw = today ? snapshot.today_change : snapshot.since_previous_close;
  const value = pct ?? (snapshot.metadata?.change_bps !== undefined ? snapshot.metadata.change_bps : raw);
  if (value === null || value === undefined) return { text: "—", className: "" };
  const suffix = pct !== null && pct !== undefined ? "%" : snapshot.metadata?.change_bps !== undefined ? " bp" : "";
  return { text: `${value > 0 ? "+" : ""}${Number(value).toFixed(2)}${suffix}`, className: value > 0 ? "positive" : value < 0 ? "negative" : "" };
}
function child(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

async function api(url, options) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.error || `HTTP ${response.status}`);
  return payload;
}

async function loadHealth() {
  try {
    const health = await api("/api/health");
    const badge = $("#service-status");
    badge.classList.add("ok");
    badge.lastChild.textContent = ` Codex · ${health.codexAuth}`;
  } catch {
    setText("#service-status", "服务未连接");
  }
}

function renderSnapshot(bundle) {
  state.snapshot = bundle;
  const rows = Object.values({ ...(bundle.core || {}), ...(bundle.target_specific || {}) });
  const table = $("#market-table");
  table.replaceChildren();
  if (!rows.length) {
    const tr = child("tr"); const td = child("td", "empty", "没有可用市场快照"); td.colSpan = 5; tr.append(td); table.append(tr);
  }
  for (const snapshot of rows) {
    const tr = child("tr");
    tr.append(child("td", "", snapshot.label || snapshot.key));
    tr.append(child("td", "", formatNumber(snapshot.current, snapshot.unit)));
    const previous = formatChange(snapshot, false);
    tr.append(child("td", previous.className, previous.text));
    const today = formatChange(snapshot, true);
    tr.append(child("td", today.className, today.text));
    const freshCell = child("td");
    freshCell.append(child("span", `freshness ${snapshot.freshness || "unknown"}`, snapshot.freshness || "unknown"));
    tr.append(freshCell); table.append(tr);
  }
  const stale = bundle.data_quality?.stale_or_unknown || [];
  const errors = Object.values(bundle.errors || {});
  const session = bundle.session_date
    ? `${bundle.session_date} · ${bundle.session} (${bundle.session_timezone || "timezone unknown"})`
    : bundle.session || "session unknown";
  setText("#data-note", `${session} · generated ${bundle.generated_at || "unknown"} UTC · stale/unknown: ${stale.length ? stale.join(", ") : "无"}${errors.length ? ` · 数据缺口: ${errors.join("；")}` : ""}`);
  renderEvents(bundle.events || []);
}

function renderEvents(events) {
  setText("#event-count", String(events.length));
  const list = $("#events-list"); list.replaceChildren();
  if (!events.length) { list.append(child("p", "empty", "今日事件数据不可用或没有中高影响事件")); return; }
  for (const event of events) {
    const item = child("div", "event-item");
    const time = event.time_utc ? new Date(event.time_utc).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false, timeZone: "Asia/Shanghai" }) : "待定";
    item.append(child("div", "event-time", time));
    const body = child("div"); body.append(child("div", "event-title", `${event.currency || event.country} · ${event.name}`));
    const precision = event.time_precision === "estimated" ? " · 时间待定" : "";
    body.append(child("div", "event-meta", `UTC+8${precision} · 重要度 ${event.importance} · 前值 ${event.previous ?? "—"} · 预期 ${event.forecast ?? "—"} · 实际 ${event.actual ?? "待公布"}`));
    item.append(body); list.append(item);
  }
}

function renderReport(report, isFollowUp = false) {
  const regime = report.regime || {};
  setText("#regime-event", regime.eventRisk); setText("#regime-usd", regime.usd); setText("#regime-rates", regime.rates);
  setText("#regime-risk", regime.riskAppetite); setText("#regime-vol", regime.volatility); setText("#regime-consistency", regime.consistency);
  setText("#report-headline", report.headline); setText("#market-narrative", report.whatMarketsPricing);
  setText("#generated-time", report.generatedAt || new Date().toISOString());
  const divergences = $("#divergence-list"); divergences.replaceChildren();
  if (!(report.divergences || []).length) divergences.append(child("p", "empty", "未发现足够明确的跨市场背离"));
  for (const divergence of report.divergences || []) {
    const box = child("div", "divergence-item"); box.append(child("strong", "", divergence.title)); box.append(child("p", "", divergence.explanation)); divergences.append(box);
  }
  const assets = $("#asset-backgrounds"); assets.replaceChildren();
  for (const asset of report.assetBackgrounds || []) {
    const card = child("div", "asset-context"); card.append(child("strong", "", asset.asset)); card.append(child("p", "", asset.context)); assets.append(card);
  }
  if (!assets.children.length) assets.append(child("p", "empty", "没有独立资产背景"));
  if (report.events?.length) renderReportEvents(report.events);
  if (isFollowUp || report.answer) {
    const answer = $("#answer-box"); answer.textContent = report.answer || report.whatMarketsPricing; answer.classList.remove("hidden");
  }
}

function renderReportEvents(events) {
  const normalized = events.map((event) => ({
    time_utc: event.time,
    currency: event.currency,
    name: event.name,
    importance: event.importance,
    actual: event.actual,
    forecast: event.forecast,
    previous: event.previous,
  }));
  renderEvents(normalized);
}

function showProgress(title, detail) {
  $("#analysis-progress").classList.remove("hidden"); setText("#progress-title", title); setText("#progress-detail", detail);
}
function hideProgress() { $("#analysis-progress").classList.add("hidden"); }

async function loadSnapshot() {
  const requestId = ++state.snapshotRequest;
  const target = state.target;
  showProgress("正在载入市场数据", "读取当前值、前收、今日变化和数据新鲜度…");
  try {
    const bundle = await api(`/api/snapshot?target=${encodeURIComponent(target)}`);
    if (requestId === state.snapshotRequest && target === state.target) renderSnapshot(bundle);
  } catch (error) {
    if (requestId === state.snapshotRequest) setText("#data-note", `快照失败：${error.message}`);
  } finally {
    if (requestId === state.snapshotRequest && !state.analyzing) hideProgress();
  }
}

async function runAnalysis(question = "", followUp = false) {
  if (state.analyzing) return;
  state.analyzing = true;
  showProgress("Codex 正在分析跨市场关系", "检查一致性、背离、主要驱动与今日事件风险…");
  const stageTimers = [
    setTimeout(() => showProgress("Codex 正在组织市场叙事", "已完成数据采集，正在区分确认关系、背离与数据缺口…"), 35_000),
    setTimeout(() => showProgress("Codex 仍在推理", "部分网络环境会让 Codex 自动从 WebSocket 降级到 HTTPS，请继续等待…"), 105_000),
  ];
  $("#analyze-button").disabled = true;
  try {
    const result = await api("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: state.target, question, threadId: followUp ? state.threadId : null }),
    });
    state.threadId = result.threadId || state.threadId;
    if (result.snapshot) renderSnapshot(result.snapshot);
    renderReport(result.report, followUp || Boolean(question));
  } catch (error) {
    const answer = $("#answer-box"); answer.textContent = `Codex 分析失败：${error.message}\n\n原始市场快照仍可在上方查看。请检查 Codex 登录/API key 与经济日历配置。`; answer.classList.remove("hidden");
  } finally {
    stageTimers.forEach(clearTimeout);
    state.analyzing = false; $("#analyze-button").disabled = false; hideProgress();
  }
}

$$('.market-tab').forEach((button) => button.addEventListener("click", async () => {
  $$('.market-tab').forEach((tab) => tab.classList.remove("active")); button.classList.add("active");
  state.target = button.dataset.target; state.threadId = null; $("#answer-box").classList.add("hidden"); await loadSnapshot();
}));
$("#refresh-data").addEventListener("click", loadSnapshot);
$("#analyze-button").addEventListener("click", () => runAnalysis());
$("#ask-form").addEventListener("submit", (event) => {
  event.preventDefault(); const question = $("#question-input").value.trim(); if (question) runAnalysis(question, true);
});

setInterval(() => { setText("#clock", `${new Date().toLocaleTimeString("zh-CN", { hour12: false, timeZone: "Asia/Shanghai" })} UTC+8`); }, 1000);
loadHealth(); loadSnapshot();
