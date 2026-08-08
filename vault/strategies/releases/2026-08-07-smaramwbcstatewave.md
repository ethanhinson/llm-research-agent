---
title: "smaramwbc/statewave"
date: 2026-08-07
type: release
score: 7
score_label: significance
tags: [release, memory, agent-frameworks, context-window]
validated: false
sources_count: 1
content_source: full
status: new
---

# smaramwbc/statewave

## Summary
Statewave is an open-source memory runtime for AI agents that provides deterministic, provenance-tagged context without retrieval-time sampling noise. It organizes memories around subjects (users, accounts, entities) and guarantees that identical queries against the same subject at the same point in time produce identical output through compile-once architecture.

## How It Works
Statewave follows an ingest → compile → retrieve loop. Raw events (episodes) are appended to a subject's log. A pluggable compiler (heuristic or LLM-backed) processes these episodes once per subject change into typed, scored memories with content-hash receipts. On demand, the runtime assembles ranked, token-bounded context bundles ready for prompts, with full provenance tracing each memory back to its source episodes. The system is idempotent at every step — recompiling a subject produces no duplicates, and reassembling a bundle for the same task returns identical bytes. It runs self-hosted on Postgres + pgvector, offers subject-scoped multi-tenancy, and exposes a REST API with Python and TypeScript SDKs.

## Why It Matters
Most AI applications lose context between sessions and lack durable memory; vector databases and chat-log injection create fragile, unstructured context that degrades at scale. Statewave solves this by replacing query-time retrieval (which introduces sampling variance) with deterministic, compile-then-use memories tied to clear data lifecycles and subject timelines. Practitioners can inspect provenance, enforce declarative policies over sensitivity labels (PII, financial, secret), and guarantee reproducible answers—critical for customer support, long-running agents, and compliance-sensitive use cases. The framework is language-agnostic, requires no GPU for the API layer, and runs entirely on infrastructure you control.

## Sources
- [smaramwbc/statewave](https://github.com/smaramwbc/statewave) — github · 290

## Related
