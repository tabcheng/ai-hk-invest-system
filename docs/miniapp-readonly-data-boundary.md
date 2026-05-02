# Mini App Read-only Data Surface Boundary Plan (Step 75, docs-only)

## Scope and intent
This document defines the **next-step boundary plan** for moving from the current static Mini App shell (Phase 1) to a future **data-enabled but read-only** surface.

This is a docs-only planning step.

## Background context
- Step 73 completed Railway `miniapp-static-preview` static deployment and acceptance.
- Step 74 completed Mini App static shell polish and static-contract test hardening.
- Current Mini App remains static/read-only/framework-free and does not perform production Supabase read, Telegram auth validation, or write actions.

Explicit non-goals in Step 75:
- no runtime API implementation
- no Telegram auth validation code
- no Supabase client/browser production read
- no Supabase schema or RLS policy change
- no Mini App JS data-fetch integration
- no write action, decision capture, or paper order creation
- no broker/live execution path
- no Railway topology or env-var change

## A) Recommended data path (future implementation target)
1. Mini App browser sends Telegram `initData` to backend.
2. Backend validates `initData` **server-side**.
3. Backend enforces operator allowlist / authorization checks.
4. Backend reads bounded data from Supabase/internal services.
5. Backend returns bounded read-only JSON response.
6. Mini App renders read-only review cards.

## B) Explicitly rejected path for now
- No direct browser-to-Supabase production reads.
- No Supabase service-role/secret key in browser/client code.
- No vendor API secret in browser/client code.
- No broker key in browser/client code.
- No use of `initDataUnsafe` for authorization decisions.

## C) First read-only data candidates (definition only)
Candidate sections for first data-enabled read-only surface:
- latest runner status
- recent runs / latest run id
- daily review packet summary
- paper PnL / risk snapshot
- outcome review summary

This section is a planning contract only; no API/data implementation is included in Step 75.

## D) Deferred / excluded data from first read-only surface
Keep out of first read-only data surface:
- strategy mutation
- decision capture
- paper order creation
- broker/live execution
- raw unrestricted Supabase table browsing
- vendor secret-backed market-data calls from browser
- write-capable endpoints

## E) Conceptual read-only response contract (example)
```json
{
  "status": "ok",
  "generated_at_hkt": "2026-05-02T20:00:00+08:00",
  "sections": {
    "runner_status": {},
    "daily_review": {},
    "pnl_snapshot": {},
    "outcome_review": {}
  },
  "guardrails": {
    "read_only": true,
    "paper_trade_only": true,
    "no_broker_execution": true
  }
}
```

Notes:
- `generated_at_hkt` is for review readability and should be explicit about timezone semantics.
- Response must stay bounded to review fields; no write semantics or execution intents.

## F) Acceptance criteria for future implementation step
Any future runtime implementation for Mini App read-only data must prove:
1. server-side `initData` validation exists;
2. authorization is enforced;
3. no secrets are exposed to browser/client bundles;
4. no write path exists;
5. response remains bounded/read-only;
6. output retains paper-trading/decision-support wording;
7. webhook and daily runner services remain unaffected.

## Domain boundary reminder
The AI HK Invest system remains paper-trading/decision-support only:
- AI simulated decision
- human paper decision
- real trade decision outside system

No broker integration or autonomous real-money execution is authorized by this plan.
