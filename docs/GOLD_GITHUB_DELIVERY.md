# Gold Workbench delivery · 2026-09-22

## Architecture

GitHub Actions → restore authenticated encrypted SQLite → collect Yahoo/FRED/CFTC → evaluate due outcomes → freeze approved Gold model → optional DeepSeek/Kimi commentary → encrypted state archive + append-only public ledger → GitHub Pages.

Pages hosts static files, not a Python server. It remains readable without Codex or a local computer. Weekday collection is scheduled at **06:17 UTC / 14:17 Beijing**. GitHub schedules may run late and public-repository schedules can be disabled after 60 days without repository activity; monitor Actions, keep an external heartbeat if unattended for longer. The page marks stale forecasts after 96 hours. This is scheduled daily research, not realtime pricing.

## Research boundary

The existing `Gold.GCProxy.G001.shadow` numerical code and parameters remain frozen. Delivery modules do not fit or promote a model. All horizon forecasts still have `No Edge`. D5 is five observed sessions after the first observed close strictly after the UTC issue date; it is not a weekly candle or next-Friday forecast. H4 lacks qualified hourly data. Neutral does not predict a sideways market.

River: raw source/value/time → standardized input and fitted coefficient → additive family contribution → bounded final score. The intercept is a separate stream. Line width represents absolute contribution, not probability. Context/risk/disabled branches carry no directional weight. Original frozen prediction JSON remains available from every ledger row. Prices shown are GC continuous proxy; no relabeling as XAUUSD.

## API configuration

The window supports DeepSeek, international Kimi and China Kimi, editable model ID, session-only key, explicit connection test, Chinese/English commentary. The key is never stored in localStorage or exported. The only browser preference stored is language. Browser direct requests are subject to provider CORS; a useful failure message points to scheduled or local use. The local same-origin endpoint uses allowlisted official provider URLs and never returns upstream error bodies.

For automatic bilingual AI commentary, set repository Secrets `DEEPSEEK_API_KEY` or `MOONSHOT_API_KEY`, and Variables `ORACLE_AI_PROVIDER=deepseek|kimi|kimi-cn` and optional `ORACLE_AI_MODEL`. Default is `off`; the numerical pipeline and six-module deterministic report run without credentials. A DeepSeek key does not authenticate to Kimi. Previously pasted keys are not embedded or automatically republished to GitHub.

Official references checked: [DeepSeek](https://api-docs.deepseek.com/zh-cn/), [Kimi](https://platform.kimi.ai/docs/overview), [Pages](https://docs.github.com/en/get-started/start-your-journey/deploying-your-website-automatically).

## Persistence and recovery

1. `ORACLE_STATE_KEY` is a generated Fernet key stored in repository Actions Secrets. `gold-state` release assets hold authenticated encrypted gzip SQLite snapshots, including raw payloads. Encryption key is never in source, Pages or logs. Do not delete/rotate the key without a planned migration and separately recoverable plaintext backup.
2. Each run restores the latest encrypted archive and verifies SQLite integrity and evidence hashes. It refuses a missing archive or model/code mismatch. It never quietly initializes a new ledger or trains a replacement model.
3. After a successful restore, state is re-archived even if collection/export fails. Snapshots have unique run/attempt names. No old snapshot is overwritten. Archive size and repository quotas require monitoring as history grows; multi-year operation should move encrypted backups to managed object storage with lifecycle policy.
4. Public `ledger` branch keeps frozen predictions and append-only outcomes, with no raw histories or credentials. A missing or changed prediction or changed existing outcome blocks publication. New outcomes may only fill previously pending slots. The full ledger is exported, not just 200 recent records.
5. Failed runs preserve the previous Pages deployment. Check Actions for failures; the site date warning catches prolonged missed runs. Daily collection does not depend on a visitor opening the website.
6. The initial seed is an authenticated backup of the existing local ledger, preserving its original IDs/model and history. Raw market archive redistribution rights remain source-specific; encryption does not grant a data license. Public output is derived research, with explicit source attribution.

## Trader-report methods adopted

Borrowed: opportunity cost, policy expectation versus announcement, price response, cross-market divergence, positioning and follow-up conditions. These appear as descriptive Context and missing-data prompts. [WGC GRAM](https://www.gold.org/goldhub/tools/gold-return-attribution-model) explicitly provides historical weekly/monthly attribution, not proof of next-week forecasting.

The pasted report's September 16 Fed +25bp decision and 3.75–4.00% range were checked against the [official FOMC statement](https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm). Other quoted prices, institution targets and geopolitical details are not treated as verified observations. The official Fed RSS feed is collected with retrieval time, publication time and content hash; headlines are context-only, not policy-surprise scores. No dynamic source quietly replaces missing pre-release consensus, geopolitical feed, ETF tonnes or options history.

Potential future experiment: preregister a policy-surprise / price-response variable once timestamped pre-release expectations and qualified reaction-window prices exist. Today's delivery makes no new predictive claim and opens no new holdout.

## Local operation

`pip install -r requirements-delivery.txt`

`python scripts/gold_delivery.py export --output dist` builds the public bundle from the existing local database.

`python scripts/gold_cloud.py --collect` runs the same collection/evaluation/freeze/export job locally, using the approved model.

`node web/server.mjs` serves the existing local site plus `/asset.html` and the same-origin optional AI gateway. Set `PORT`, `PYTHON_COMMAND`, `ORACLE_DB` as needed. The original six-module Market Context route remains in the local app; the Pages bundle opens Gold directly.
