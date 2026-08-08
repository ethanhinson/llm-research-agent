---
title: "Learning When to Trust via Selective Context Preference Optimization"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: prompting
tags: [research, prompting, instruction-following, safety-alignment]
validated: true
sources_count: 2
content_source: full
status: new
---

# Learning When to Trust via Selective Context Preference Optimization

## Summary
Language models often fail when given misleading external context, but simply training them to ignore context makes them unreliable when that context is actually helpful. This work introduces MIST, a benchmark and evaluation framework, along with SCOPE, a training method that teaches models when to trust or distrust contextual signals rather than adopting a blanket strategy.

## How It Works
MIST annotates reasoning items across four matched conditions: clean context, misleading context, correct context, and irrelevant context. The SC2W metric measures how often a misleading signal flips a correct answer to wrong. SCOPE then applies Direct Preference Optimization (DPO) over paired preferences balanced equally across all four conditions, rather than optimizing only against misleading examples. This trains the model to maintain accuracy in clean/correct/irrelevant scenarios while resisting misleading signals.

## Why It Matters
Selective trust is a more nuanced and practical objective than blanket robustness. Models need to both reject bad context and leverage good context—a capability that existing approaches fail to balance. By reframing the problem and providing matched training data across multiple conditions, practitioners can build systems that remain useful in real deployments where external signals are often reliable, not universally adversarial.

## Sources
- [Learning When to Trust via Selective Context Preference Optimization](http://arxiv.org/abs/2608.06377v1) — arxiv/search · 0

## Related
