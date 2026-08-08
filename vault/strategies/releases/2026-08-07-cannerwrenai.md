---
title: "Canner/WrenAI"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, agent-frameworks, code-generation]
validated: false
sources_count: 1
content_source: full
status: new
---

# Canner/WrenAI

## Summary
WrenAI is an open-source generative BI engine that enables AI agents to generate, deploy, and govern SQL queries and dashboards across 22+ data sources. It combines a governed text-to-SQL engine with an open semantic layer (MDL) and AI context layer to produce trustworthy business intelligence outputs grounded in reviewable, version-controlled business definitions.

## How It Works
Agents interact with WrenAI via a lightweight CLI stub (~50 lines) installed in tools like Claude Code or Cursor. The workflow is agent-driven: (1) **Generate** — agents write schema-aware, dry-plan-validated SQL against a semantic layer (MDL) that encodes business logic, definitions, and approved joins; (2) **Know** — business context lives in Git-friendly, versionable files (semantic models, instructions, memory); (3) **Deploy** — agents turn answers into shareable dashboards via wren-core-wasm and ship them to Vercel or Cloudflare Pages. The semantic layer (MDL) decouples business meaning from warehouse schema, pairing it with an AI context layer (memory, examples, unstructured company knowledge) and governed execution (row limits, structured errors, dry-plan validation).

## Why It Matters
Practitioners building AI-driven BI face a trust problem: raw LLM agents produce plausible but wrong SQL, and business logic lives scattered across databases, docs, and prompts. WrenAI solves this by making the semantic layer and context layer open, reviewable, and version-controlled—usable by any agent, not locked in a vendor UI. The governed execution primitives and structured error handling keep agent-generated SQL inside guardrails while maintaining an auditable trace, making it practical to delegate BI generation to agents without sacrificing correctness or governance.

## Sources
- [Canner/WrenAI](https://github.com/Canner/WrenAI) — github · 17179

## Related
