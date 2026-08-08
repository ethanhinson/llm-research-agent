---
title: "CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks"
date: 2026-08-07
type: research
score: 7
score_label: novelty
category: agentic
tags: [research, agentic, agent-frameworks, rlhf, reasoning]
validated: true
sources_count: 3
content_source: full
status: new
---

# CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks

## Summary
CalibForge is an autonomous system for generating terminal tasks (executable coding problems) calibrated to be appropriately challenging for training agents. It uses adversarial solver calibration—testing tasks against multiple solvers—to iteratively revise candidate tasks so they occupy a learnable zone relative to solver capability, rather than being trivially solvable or intractable.

## How It Works
CalibForge employs two calibration strategies. Multi-solver calibration targets disagreement across a heterogeneous pool of solvers, identifying tasks where solver performance diverges. Contrastive solver calibration targets a specific strong-pass/weak-fail relation—tasks that a strong solver can handle but a weak solver cannot. Both approaches anchor task difficulty in demonstrated solvability, using verified solver behavior to revise tasks iteratively. The system produced 5,431 calibrated tasks used to train models achieving 32.58% and 47.57% on Terminal-Bench 2.0.

## Why It Matters
Practitioners training terminal agents (code-solving systems) need training tasks that are executable, verifiable, and calibrated to difficulty—not merely solvable. Ablations show solver-relative calibration substantially outperforms manual authoring and single-solver feedback alone. Models trained on CalibForge tasks show large gains: up to 24.71 points on Terminal-Bench 2.0, 27.68 on SWE-bench Pro, and 30.04 on Doc2Repo. This demonstrates that grounding task synthesis in solver disagreement and learnable-zone targeting produces more effective and transferable training data than conventional approaches.

## Sources
- [CalibForge: Adversarial Solver Calibration for Scaling Learnable Terminal Tasks](http://arxiv.org/abs/2608.06352v1) — arxiv/search · 0

## Related
