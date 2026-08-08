---
title: "Tytan: Interactive Neurosymbolic Construction of Analytic Semantic Schemas from Relational Data"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: tooling
tags: [research, tooling, semantic-parsing, structured-extraction]
validated: false
sources_count: 1
content_source: full
status: new
---

# Tytan: Interactive Neurosymbolic Construction of Analytic Semantic Schemas from Relational Data

## Summary
TYTAN is a system that automatically constructs analytic semantic schemas from relational databases by combining symbolic database analysis with LLM-based inference. It addresses the manual knowledge-acquisition bottleneck that currently limits scalability of data analysis tools and keeps non-technical users dependent on experts.

## How It Works
TYTAN analyzes the database structure symbolically and uses LLM-based semantic inference to propose entities, assign roles (measures, identifiers, etc.), and generate names. When evidence is ambiguous, the system asks the user targeted natural-language questions rather than making arbitrary decisions. The approach integrates user-provided descriptions when available.

## Why It Matters
TYTAN demonstrates near-perfect functional utility across three critical dimensions: it achieves 100% coverage of entities and features, 100% retrieval correctness (all 1,678 self-generated schema instructions executed correctly), and 92–100% semantic role accuracy. Performance on a held-out blind test with no declared keys showed full entity structure recovery, indicating the system generalizes beyond its training domains and could reduce manual schema curation work that currently gates access to data analysis for non-experts.

## Sources
- [Tytan: Interactive Neurosymbolic Construction of Analytic Semantic Schemas from Relational Data](http://arxiv.org/abs/2608.06331v1) — arxiv · 0

## Related
