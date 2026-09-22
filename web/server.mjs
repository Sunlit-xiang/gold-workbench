import { spawn } from "node:child_process";
import { createServer as createHttpServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { REPORT_SCHEMA, buildPrompt, normalizeTarget, parseReport } from "./oracle.mjs";

const webRoot = path.dirname(fileURLToPath(import.meta.url));
const projectRoot = path.resolve(webRoot, "..");
const publicRoot = path.join(webRoot, "public");
const port = Number(process.env.PORT || 3000);
const pythonCommand = process.env.PYTHON_COMMAND || "python";
const codexTimeoutMs = Number(process.env.CODEX_TIMEOUT_MS || 360_000);
let codex;
const ASSET_REGISTRY = [{ id: "gold", name: "Gold · GC Proxy", url: "/asset.html?asset=gold" }];

const MIME_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
};

function json(response, statusCode, payload) {
  const body = JSON.stringify(payload);
  response.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(body),
    "Cache-Control": "no-store",
  });
  response.end(body);
}

async function readJsonBody(request) {
  const chunks = [];
  let size = 0;
  for await (const chunk of request) {
    size += chunk.length;
    if (size > 128 * 1024) {
      throw new Error("request body is too large");
    }
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function runSnapshot(target, session = "auto") {
  return new Promise((resolve, reject) => {
    const child = spawn(
      pythonCommand,
      ["scripts/intraday_snapshot.py", "--target", target, "--session", session],
      {
        cwd: projectRoot,
        env: { ...process.env, PYTHONUTF8: "1" },
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
      },
    );
    const stdout = [];
    const stderr = [];
    const timeout = setTimeout(() => {
      child.kill();
      reject(new Error("market snapshot timed out after 45 seconds"));
    }, 45_000);
    child.stdout.on("data", (chunk) => stdout.push(chunk));
    child.stderr.on("data", (chunk) => stderr.push(chunk));
    child.on("error", (error) => {
      clearTimeout(timeout);
      reject(error);
    });
    child.on("close", (code) => {
      clearTimeout(timeout);
      if (code !== 0) {
        reject(new Error(Buffer.concat(stderr).toString("utf8") || `snapshot exited ${code}`));
        return;
      }
      try {
        resolve(JSON.parse(Buffer.concat(stdout).toString("utf8")));
      } catch (error) {
        reject(new Error(`snapshot returned invalid JSON: ${error.message}`));
      }
    });
  });
}

async function analyze({ target, question, session, threadId, snapshot }) {
  if (!codex) {
    const { Codex } = await import("@openai/codex-sdk");
    codex = new Codex(process.env.CODEX_API_KEY ? { apiKey: process.env.CODEX_API_KEY } : {});
  }
  const options = {
    workingDirectory: projectRoot,
    sandboxMode: "read-only",
    approvalPolicy: "never",
    networkAccessEnabled: true,
    webSearchMode: "disabled",
    modelReasoningEffort: "medium",
  };
  const thread = threadId ? codex.resumeThread(threadId, options) : codex.startThread(options);
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), codexTimeoutMs);
  try {
    const turn = await thread.run(buildPrompt({ target, question, session, snapshot }), {
      outputSchema: REPORT_SCHEMA,
      signal: controller.signal,
    });
    return {
      threadId: thread.id,
      report: parseReport(turn.finalResponse),
      usage: turn.usage,
    };
  } catch (error) {
    if (controller.signal.aborted) {
      throw new Error(`Codex analysis timed out after ${Math.round(codexTimeoutMs / 1000)} seconds`);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

async function serveStatic(requestUrl, response) {
  const pathname = requestUrl.pathname === "/" ? "/index.html" : requestUrl.pathname;
  const decoded = decodeURIComponent(pathname);
  const filePath = path.resolve(publicRoot, `.${decoded}`);
  if (!filePath.startsWith(publicRoot)) {
    json(response, 403, { error: "forbidden" });
    return;
  }
  try {
    const info = await stat(filePath);
    if (!info.isFile()) throw new Error("not a file");
    const body = await readFile(filePath);
    response.writeHead(200, {
      "Content-Type": MIME_TYPES[path.extname(filePath)] || "application/octet-stream",
      "Content-Length": body.length,
      "Cache-Control": "no-cache",
    });
    response.end(body);
  } catch {
    json(response, 404, { error: "not found" });
  }
}

export function runAssetDashboard(assetId = "gold", predictionId = null) {
  return new Promise((resolve, reject) => {
    if (assetId !== "gold") return reject(new Error("Asset not registered in Python runtime"));
    const args = ["scripts/asset_pipeline.py", ...(predictionId ? ["prediction", "--id", predictionId] : ["dashboard"])];
    if (process.env.ORACLE_DB) args.push("--db", process.env.ORACLE_DB);
    const child = spawn(pythonCommand, args, { cwd: projectRoot, windowsHide: true, env: { ...process.env, PYTHONIOENCODING: "utf-8" } });
    const stdout = [], stderr = [];
    let size = 0;
    const timer = setTimeout(() => { child.kill(); reject(new Error("asset dashboard timed out")); }, 30000);
    child.stdout.on("data", (data) => { size += data.length; if (size > 12 * 1024 * 1024) child.kill(); else stdout.push(data); });
    child.stderr.on("data", (data) => stderr.push(data));
    child.on("error", (error) => { clearTimeout(timer); reject(error); });
    child.on("close", (code) => {
      clearTimeout(timer);
      if (code !== 0) return reject(new Error(Buffer.concat(stderr).toString("utf8") || "asset pipeline failed"));
      try { resolve(JSON.parse(Buffer.concat(stdout).toString("utf8"))); } catch (error) { reject(error); }
    });
  });
}

function runGoldDelivery(command, input = null) {
  return new Promise((resolve, reject) => {
    const args = ["scripts/gold_delivery.py", command];
    if (process.env.ORACLE_DB) args.push("--db", process.env.ORACLE_DB);
    const child = spawn(pythonCommand, args, {cwd:projectRoot, windowsHide:true, env:{...process.env,PYTHONIOENCODING:"utf-8"}});
    const stdout=[];let size=0;
    const timer=setTimeout(()=>{child.kill();reject(new Error("Gold delivery timed out"));},110000);
    child.stdout.on("data",chunk=>{size+=chunk.length;if(size>16*1024*1024)child.kill();else stdout.push(chunk);});
    // Provider exception bodies and keys must never enter HTTP errors.
    child.stderr.resume();
    child.on("error",()=>{clearTimeout(timer);reject(new Error("Gold runtime unavailable"));});
    child.on("close",code=>{clearTimeout(timer);if(code!==0)return reject(new Error("Gold delivery failed; inspect runtime health"));try{resolve(JSON.parse(Buffer.concat(stdout).toString("utf8")));}catch{reject(new Error("Invalid delivery response"));}});
    child.stdin.end(input ? JSON.stringify(input) : "");
  });
}

export function createServer({ snapshotRunner = runSnapshot, analyzer = analyze, assetReader = runAssetDashboard, goldReader = runGoldDelivery } = {}) {
  return createHttpServer(async (request, response) => {
    const requestUrl = new URL(request.url || "/", `http://${request.headers.host || "localhost"}`);
    try {
      if (request.method === "GET" && requestUrl.pathname === "/api/gold/dashboard") {
        json(response, 200, await goldReader("dashboard"));
        return;
      }
      if (request.method === "POST" && requestUrl.pathname === "/api/gold/commentary") {
        // Loopback service: reject browser cross-origin requests and DNS-rebinding hosts.
        const host = request.headers.host || "";
        const origin = request.headers.origin;
        if (!/^(127\.0\.0\.1|localhost)(:\d+)?$/.test(host) || (origin && origin !== `http://${host}`)) {
          json(response,403,{error:"Same-origin local requests only"});return;
        }
        if (!String(request.headers["content-type"]).startsWith("application/json")) {
          json(response,415,{error:"JSON required"});return;
        }
        const body=await readJsonBody(request);
        if (!['deepseek','kimi','kimi-cn'].includes(body.provider) || !['zh','en'].includes(body.language) || typeof body.model!=='string' || body.model.length>100 || typeof body.api_key!=='string' || body.api_key.length>512) {
          json(response,400,{error:"Invalid provider settings"});return;
        }
        json(response,200,await goldReader("commentary",{provider:body.provider,model:body.model,language:body.language,api_key:body.api_key}));return;
      }
      if (request.method === "GET" && requestUrl.pathname === "/api/assets") {
        json(response, 200, { assets: ASSET_REGISTRY });
        return;
      }
      const assetMatch = requestUrl.pathname.match(/^\/api\/assets\/([a-z][a-z0-9_-]{0,30})$/);
      if (request.method === "GET" && assetMatch && ASSET_REGISTRY.some(asset => asset.id === assetMatch[1])) {
        json(response, 200, await assetReader(assetMatch[1]));
        return;
      }
      const predictionMatch = requestUrl.pathname.match(/^\/api\/assets\/([a-z][a-z0-9_-]{0,30})\/predictions\/([a-f0-9]{64})$/);
      if (request.method === "GET" && predictionMatch && ASSET_REGISTRY.some(asset => asset.id === predictionMatch[1])) {
        json(response, 200, await assetReader(predictionMatch[1], predictionMatch[2]));
        return;
      }
      if (request.method === "GET" && requestUrl.pathname === "/api/health") {
        json(response, 200, {
          ok: true,
          service: "digital-oracle-web",
          codexAuth: process.env.CODEX_API_KEY ? "api-key" : "local-session",
          codexTimeoutSeconds: Math.round(codexTimeoutMs / 1000),
          calendarConfigured: Boolean(process.env.TRADING_ECONOMICS_API_KEY),
        });
        return;
      }
      if (request.method === "GET" && requestUrl.pathname === "/api/snapshot") {
        const target = normalizeTarget(requestUrl.searchParams.get("target"));
        const session = requestUrl.searchParams.get("session") || "auto";
        json(response, 200, await snapshotRunner(target, session));
        return;
      }
      if (request.method === "POST" && requestUrl.pathname === "/api/analyze") {
        const body = await readJsonBody(request);
        const target = normalizeTarget(body.target);
        const question = String(body.question || "").trim();
        const session = String(body.session || "auto");
        if (question.length > 4000) throw new Error("question is too long");
        const snapshot = await snapshotRunner(target, session);
        const result = await analyzer({
          target,
          question,
          session,
          threadId: body.threadId ? String(body.threadId) : null,
          snapshot,
        });
        json(response, 200, { ...result, snapshot });
        return;
      }
      if (requestUrl.pathname.startsWith("/api/")) {
        json(response, 404, { error: "unknown API endpoint" });
        return;
      }
      await serveStatic(requestUrl, response);
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      json(response, 500, { error: message });
    }
  });
}

if (process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href) {
  const server = createServer();
  server.listen(port, "127.0.0.1", () => {
    console.log(`Digital Oracle: http://localhost:${port}`);
  });
}
