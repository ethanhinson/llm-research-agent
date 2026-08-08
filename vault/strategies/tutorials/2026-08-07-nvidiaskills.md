---
title: "NVIDIA/skills"
date: 2026-08-07
type: tutorial
score: 7
score_label: practicality
tags: [tutorial, tool-use, agent-frameworks]
validated: false
sources_count: 1
content_source: full
status: new
---

# NVIDIA/skills

## Summary
NVIDIA/skills is an official catalog of NVIDIA-verified instruction sets for teaching AI coding agents (Claude Code, Codex, Cursor, and others) how to use NVIDIA software optimally. Skills cover physical AI, robotics, CUDA libraries, RAG, and platform tools, and are maintained in product repos with daily automated sync to the central catalog.

## How It Works
Skills are installed via CLI (`npx skills add nvidia/skills`) with optional targeting by skill name and agent type. Each published skill includes a SKILL.md instruction file, metadata card, detached OMS signature (verifiable against `nv-agent-root-cert.pem`), and evaluation datasets. The sync pipeline enforces compliance gates—dropping any skill missing required artifacts—and skills are syndicated to multiple marketplaces (Skills.sh, Claude Code plugin, Codex plugin, etc.). Users can list available skills, update existing installations, and verify signatures using the `model-signing` tool.

## Why It Matters
This infrastructure lets practitioners reliably extend AI agents with curated NVIDIA tooling without manual integration. The signing and verification layer provides supply-chain integrity assurance, the daily sync keeps skills current, and support across multiple agents (Claude Code, Codex, Cursor, Kiro, Cortex) reduces friction when deploying agents in different environments. Practitioners dealing with CUDA, optimization, simulation, or robotics workflows gain immediate, verified access to domain-specific guidance without building custom integrations.

## Sources
- [NVIDIA/skills](https://github.com/NVIDIA/skills) — github · 2817

## Related
