# Digital Oracle agent instructions

## Asset model research and implementation

- Every asset onboarding/model change must follow `docs/UNIVERSAL_ASSET_RESEARCH_CONTRACT.md`.
- Explicit asset-model development requests permit deterministic technical factors, horizon forecasts, research evaluation and code changes. The premarket restrictions below apply to the legacy market-analysis workflow, not to this explicit research workflow.
- Read the ancestor quant-research instructions. Preregister experiments before inspecting outcomes. Never label reconstructed-history experiments as forward-validated predictions.
- Keep asset identity, data lineage, availability, model versions and append-only predictions/outcomes explicit. Never force an Edge or automatically tune to a desired hit rate.

## Scope routing

- For long-horizon prediction, probability, macro-cycle, asset-pricing, or event-market questions, read the root `SKILL.md`.
- For intraday, premarket, 今日背景, Gold/US equities/Forex/Crypto session preparation, read `skills/intraday-market-context/SKILL.md` completely and follow it as the higher-priority workflow.

## Premarket analysis

- Build current evidence with `python scripts/intraday_snapshot.py --target <target> --pretty`.
- Preserve signal routing, cross-market confirmation, divergence analysis, time alignment, and Codex judgment.
- Treat `freshness`, `market_time`, provider errors, and `data_quality` as mandatory evidence.
- Do not edit project files during a market-analysis request.
- Do not perform technical-pattern analysis or produce entries, stops, targets, trade directions, orders, or intraday probability forecasts.
- When the request contains `WEB_JSON`, return JSON only and conform to the supplied schema.
