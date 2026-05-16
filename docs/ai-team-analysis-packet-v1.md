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


## Step 136F/136G-lite bounded summary projection
- Added backend bounded summary schema `ai_team_analysis_packet_summary.v1` for `latest_system_runs.summary_json.ai_team_packet`.
- Projection is deterministic and allowlisted only (status/guardrails/counts/top_gaps/limitations + run metadata).
- Read-model guardrails remain explicit: paper-only, decision-support-only, no broker/live/order/real-money execution, no LLM/vendor call in default runtime.
- Mini App backend review-shell now exposes read-only `sections.ai_team_packet_summary` with unavailable-safe fallback for missing/malformed rows.
- No DB migration added in this step; persistence uses existing `summary_json` bounded path.

## Step 136H/136I-lite operator consumption
- Mini App renders `sections.ai_team_packet_summary` as compact read-only card (no raw JSON block).
- Telegram `/ai_team_packet` returns bounded read-only summary from `latest_system_runs.summary_json.ai_team_packet`.
- Both surfaces fail closed on missing/malformed/unsafe guardrails.
- Both surfaces keep explicit boundary wording: paper-only, decision-support-only, no broker, no live execution, no real-money execution, no order creation.


### Step 136J/136K-lite update (2026-05-16)
- AI Team surfaces remain read-only and consume bounded `latest_system_runs.summary_json.ai_team_packet` only.
- Mini App exposes compact `AI 團隊摘要` in Today tab and detailed `AI 團隊摘要 / AI Team Packet` in System tab with deterministic freshness labels (`最新` / `可能過舊` / `未能判斷`) and fail-closed unavailable behavior.
- Telegram `/ai_team_packet` is Chinese-first, bounded, read-only operator summary; no raw JSON, no secret exposure, no journal/order/runner side-effects.
- Guardrails unchanged: paper-only, decision-support-only, no broker connection, no live/real-money execution, no autonomous execution, no order creation; human operator remains final decision-maker outside system.
- Internal MVP Launch Candidate v1 acceptance requires CI green, Railway service success, latest runner row evidence, Mini App AI Team visibility checks, Telegram command checks, and secret-safe outputs.
- LLM/vendor integration remains deferred post-launch unless explicitly approved with backend-only provider abstraction and mock-first acceptance path.
