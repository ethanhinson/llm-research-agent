---
title: "OpenAI's Codex Security Review Catches 74% of Real Bugs Semgrep Misses"
date: 2026-08-07
type: release
score: 6
score_label: significance
tags: [release, code-generation, safety-alignment]
validated: false
sources_count: 1
content_source: full
status: new
---

# OpenAI's Codex Security Review Catches 74% of Real Bugs Semgrep Misses

## Summary
OpenAI launched Codex Security Review in research preview, a GitHub PR scanner that uses language-model reasoning and full repository context to identify vulnerabilities. Independent testing shows it achieves a 74% true positive rate, substantially outperforming Semgrep (20%) and Snyk (28%) on the same codebases.

## How It Works
Codex Security Review operates in three stages: identification (analyzing the repo and exploring realistic attack paths), validation (attempting to reproduce each issue to confirm it is real), and remediation (generating concrete patches). It reasons about multi-step attack paths using language-model reasoning, test-time compute, tool use, and large context—rather than signature-based or fuzzing approaches. Findings are ranked with evidence and suggested patch options. It can be triggered manually via @codex security review comments in PRs or configured for automatic scans on PR open or every push.

## Why It Matters
Traditional static analysis tools like Semgrep and SonarQube generate high noise and low signal, overwhelming teams with hundreds of mostly irrelevant alerts. Codex Security's superior true positive rate and context-aware reasoning make it practically useful by validating findings before surfacing them, reducing toil and focusing attention on real threats. It is free during preview for Enterprise, Business, Edu, and Pro GitHub plans, lowering adoption friction for teams seeking higher-fidelity security scanning in their existing PR workflow.

## Sources
- [OpenAI's Codex Security Review Catches 74% of Real Bugs Semgrep Misses](https://alphasignal.ai/news/openai-s-codex-security-review-catches-74-of-real-bugs-semgrep-misses) — web/AlphaSignal · 0

## Related
