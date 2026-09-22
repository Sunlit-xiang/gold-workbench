import assert from "node:assert/strict";
import test from "node:test";

import { createServer } from "../server.mjs";

async function withServer(callback) {
  let analyzedSnapshot;
  const server = createServer({
    snapshotRunner: async (target) => ({ target, core: {}, target_specific: {}, events: [] }),
    analyzer: async ({ target, snapshot }) => {
      analyzedSnapshot = snapshot;
      return { threadId: "test-thread", report: { target } };
    },
  });
  await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    await callback(`http://127.0.0.1:${address.port}`, () => analyzedSnapshot);
  } finally {
    await new Promise((resolve) => server.close(resolve));
  }
}

test("health, snapshot and analyze endpoints work", async () => {
  await withServer(async (baseUrl, getAnalyzedSnapshot) => {
    const health = await fetch(`${baseUrl}/api/health`).then((response) => response.json());
    assert.equal(health.ok, true);

    const snapshot = await fetch(`${baseUrl}/api/snapshot?target=gold`).then((response) => response.json());
    assert.equal(snapshot.target, "gold");

    const analyze = await fetch(`${baseUrl}/api/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target: "btc", question: "context" }),
    }).then((response) => response.json());
    assert.equal(analyze.threadId, "test-thread");
    assert.equal(analyze.report.target, "btc");
    assert.equal(analyze.snapshot.target, "btc");
    assert.equal(getAnalyzedSnapshot().target, "btc");
  });
});
