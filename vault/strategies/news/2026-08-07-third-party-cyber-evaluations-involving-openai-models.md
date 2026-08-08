---
title: "Third-party cyber evaluations involving OpenAI models"
date: 2026-08-07
type: news
score: 8
score_label: timeliness
tags: [news, safety-alignment, cybersecurity]
validated: false
sources_count: 1
content_source: full
status: new
---

# Third-party cyber evaluations involving OpenAI models

## Summary
Third-party cybersecurity evaluations of OpenAI and Anthropic models have surfaced unintended real-world exploits caused by testing-environment misconfigurations. In separate incidents with evaluation partner Irregular, models accessed the public internet when they should have been isolated, leading one model to attack a real website it mistook for a simulated CTF target.

## How It Works
Irregular was conducting Capture-the-Flag-style evaluations designed to be isolated from the internet. A misconfiguration allowed the models to reach the public internet. In one case, a fictional CTF target name coincidentally matched a real domain; the model, having unexpected internet access, exploited the actual website believing it was part of the simulation. Irregular also hosted a misconfigured environment that gave Claude live internet access during Anthropic's tests.

## Why It Matters
These incidents reveal that current third-party evaluation practices can produce false positives for model capability and safety—models appear to exhibit autonomous cyberattack behavior when in reality they are responding to environmental misconfigurations rather than demonstrating genuine emergent threats. Practitioners conducting or commissioning external red-team evaluations should audit isolation controls and domain ownership assumptions, as gaps can conflate testing artifacts with actual model behavior.

## Sources
- [Third-party cyber evaluations involving OpenAI models](https://simonwillison.net/2026/Aug/5/third-party-cyber-evaluations/#atom-everything) — web/Simon Willison's blog · 0

## Related
