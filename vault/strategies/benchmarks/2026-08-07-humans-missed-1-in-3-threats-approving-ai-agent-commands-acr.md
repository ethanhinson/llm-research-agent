---
title: "Humans missed 1 in 3 threats approving AI agent commands across 40k game runs"
date: 2026-08-07
type: benchmark
score: 8
score_label: authority
tags: [benchmark, agent-frameworks, safety-alignment]
validated: false
sources_count: 1
content_source: full
status: new
---

# Humans missed 1 in 3 threats approving AI agent commands across 40k game runs

## Summary
A browser game where players approved or denied AI agent commands under time pressure revealed that humans missed approximately 1 in 3 threats across over 40,000 runs. The benchmark demonstrates significant gaps in human-in-the-loop oversight of AI coding agents, with particular vulnerabilities around obfuscated commands and permission fatigue.

## How It Works
Players reviewed 409,000 approve/deny decisions on AI agent commands, roughly one-third of which were threats ranging from obviously destructive commands (rm -rf /) to credential exfiltration. Miss rates varied by threat type: 11.7% for obviously destructive commands, but 35.0% for scope violations like accessing ~/.aws/credentials. The most-missed attack vector was npm run commands with hidden payloads (64.7% approval rate for npm run analyze), which doubled success rates even when malicious content appeared in the history log. Miss rates increased toward the end of game sessions, consistent with permission fatigue observed in real deployments.

## Why It Matters
The results expose a fundamental flaw in relying on human-in-the-loop approval as a security boundary for AI agents. Developers face high cognitive load distinguishing benign from malicious commands without full context of file changes, leading to fatigue that pushes users toward either complete approval bypass or over-blocking that slows agents down. The gap between threat detection rates and the ease with which familiar command names can hide payloads suggests that approval-based safeguards alone are insufficient; practitioners should prioritize technical mitigations like sandboxing and permission isolation rather than depending primarily on human judgment under operational pressure.

## Sources
- [Humans missed 1 in 3 threats approving AI agent commands across 40k game runs](https://scalex.dev/blog/ai-agent-permissions-stats/) — hackernews · 329

## Related
