import assert from "node:assert/strict";
import test from "node:test";

import { buildPrompt, normalizeTarget, parseReport } from "../oracle.mjs";

test("normalizeTarget accepts supported targets and rejects others", () => {
  assert.equal(normalizeTarget(" Gold "), "gold");
  assert.throws(() => normalizeTarget("oil"), /unsupported target/);
});

test("buildPrompt keeps the premarket boundary and target", () => {
  const prompt = buildPrompt({
    target: "gold",
    question: "为什么黄金与美元同涨？",
    session: "london",
    snapshot: { target: "gold", data_quality: { complete: false } },
  });
  assert.match(prompt, /分析对象：黄金/);
  assert.match(prompt, /会话：london/);
  assert.match(prompt, /为什么黄金与美元同涨/);
  assert.match(prompt, /禁止技术形态/);
  assert.match(prompt, /"complete":false/);
  assert.match(prompt, /WEB_JSON/);
});

test("parseReport rejects non-JSON and accepts object JSON", () => {
  assert.deepEqual(parseReport('{"headline":"ok"}'), { headline: "ok" });
  assert.throws(() => parseReport("not-json"));
  assert.throws(() => parseReport("[]"), /non-object/);
});
