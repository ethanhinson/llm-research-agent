---
title: "LLMs won't break symmetric crypto"
date: 2026-08-07
type: research
score: 6
score_label: novelty
category: prompting
tags: [research, prompting, safety-alignment, reasoning]
validated: false
sources_count: 1
content_source: full
status: new
---

# LLMs won't break symmetric crypto

## Summary
Anthropic's Claude Mythos discovered new cryptanalytic attacks on reduced-round AES and the post-quantum scheme HAWK, but poses no practical threat to deployed symmetric cryptography. The work demonstrates that LLMs are unlikely to break established symmetric ciphers like AES, ChaCha, or SHA-3.

## How It Works
Mythos found a key-recovery attack on 7-round AES-128 (the full algorithm uses 10 rounds) and an attack on HAWK-512 that reduces its estimated security from 128 bits to at most 108 bits. The source text grounds these attacks in differential cryptanalysis—exploiting input–output patterns where applying differences in inputs produces statistical deviations in outputs. The text emphasizes that symmetric ciphers are deliberately designed to be "messy" and lack exploitable mathematical structure, making new attack classes unlikely.

## Why It Matters
Practitioners should recognize that symmetric cryptography represents the strongest part of deployed security systems and has already endured thousands of hours of human cryptanalytic scrutiny. Since symmetric ciphers lack clean mathematical structure and existing attack territory has been extensively explored, LLM-assisted research is better directed toward finding bugs in underanalyzed post-quantum candidates or security proofs rather than pursuing impractical attacks on well-established algorithms.

## Sources
- [LLMs won't break symmetric crypto](https://www.bfswa.blog/p/llms-wont-break-symmetric-crypto) — hackernews · 76

## Related
