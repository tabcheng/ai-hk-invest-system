# AI Team Backend Analysis Packet v1

## Purpose
Backend deterministic packet contract for AI team analysis context. This is paper-only and decision-support-only.

## Schema
- `schema_version=ai_team_analysis_packet.v1`
- run/market/signal/risk/journal/outcome contexts
- AI team slots with status/headline/inputs/gaps/confidence/limitations
- decision support section with conservative review-only next steps
- hardcoded guardrails and audit metadata

## Missing-data behavior
Missing contexts stay explicit (`not_available`/`unknown`) and reduce slot status/confidence.

## Deferred integrations (Step 136E)
- LLM: deferred until deterministic contract stabilizes; future backend-only provider with prompt/hash audit.
- Vendor: deferred; future approved provider abstraction only.
- DB: deferred; persistence/read-model expansion can be Step 136F follow-up.
- UI: deferred; Mini App/Telegram consumption can be Step 136G follow-up.
