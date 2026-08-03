<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0004 — Multi-type content evaluation — expand tagging beyond novelty](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0004-multi-type-content-evaluation.md)**
<!-- docket:backlink:end -->

# Multi-Type Content Evaluation — Design Spec

**Date:** 2026-08-02
**Status:** Approved

---

## Overview

Expand the evaluator from a single novelty-score model into a multi-type classification and evaluation pipeline. Instead of treating all LLM/AI content as "research novelty" and discarding non-research items at score 1, the system classifies each item into one of five content types and evaluates it on a type-appropriate axis. A final LLM validation pass replaces hardcoded numeric thresholds with explicit keep/skip decisions.

---

## Content Type Taxonomy

Five first-class types:

| Type | What it covers | Score axis | Score label |
|---|---|---|---|
| `research` | Novel techniques, papers, arXiv discoveries | Novelty (10=breakthrough, 1=incremental) | `novelty` |
| `release` | Model/SDK/framework/tool launches | Significance (10=landmark, 1=minor patch) | `significance` |
| `news` | Company moves, funding, trends, adoption stories | Timeliness × consequence (10=major development happening now, 1=stale/minor) | `timeliness` |
| `benchmark` | Eval results, leaderboards, model comparisons | Authority (10=rigorous methodology + credible source, 1=cherry-picked/unclear) | `authority` |
| `tutorial` | How-tos, cookbooks, implementation guides | Practicality (10=immediately actionable with clear implementation, 1=too abstract) | `practicality` |

Research items additionally carry a **sub-category** from the existing taxonomy: `prompting | architecture | agentic | tooling | use-case`. Other types do not have a sub-category.

---

## Data Model Changes

### `agent/models.py`

```python
@dataclass
class RawItem:
    title: str
    body: str
    url: str
    source: str
    engagement: int
    timestamp: str
    content_type: str = "research"   # research | release | news | benchmark | tutorial
    score: int = 0                   # replaces novelty; meaning depends on content_type
    score_label: str = "novelty"     # human-readable axis name (novelty/significance/timeliness/authority/practicality)
    keep: bool = False               # LLM's explicit keep/skip decision (pass 3)
    validated: bool = False
    sources_count: int = 1
    category: str = ""               # research sub-category only; empty for other types
    tags: list = field(default_factory=list)
```

`novelty` is removed. Downstream code that reads `item.novelty` migrates to `item.score`. `category` becomes empty string default (was `"architecture"`) since non-research items have no sub-category.

---

## Evaluator: Three-Pass Pipeline

### Pass 1 — Classify type

One API call per batch. Prompt:

```
You are classifying LLM/AI content items by type.

For each item, output exactly one line:
<n>. <type>

Types:
- research    — novel techniques, papers, arXiv findings, new approaches
- release     — product/model/SDK/framework/tool launches or major updates
- news        — company news, funding, industry trends, adoption stories
- benchmark   — eval results, leaderboards, model comparisons, capability assessments
- tutorial    — how-tos, implementation guides, cookbooks, practical walkthroughs

Items:
{items}
```

Output: updates `item.content_type` for each item in the batch.

### Pass 2 — Score per type

One API call per batch. Prompt adapts to include the type-appropriate scoring rubric for each item:

```
You are scoring LLM/AI content items. Each item has been pre-classified by type.
For each item, output exactly one line:
<n>. <score> [<subcategory>]

Scoring axis per type:
- research:   novelty 1-10  (10=breakthrough new technique, 5=incremental improvement, 1=already well-known)
  subcategory (required for research): prompting | architecture | agentic | tooling | use-case
- release:    significance 1-10  (10=landmark release that changes the field, 1=minor patch or niche tool)
- news:       timeliness 1-10  (10=major consequential development happening right now, 1=stale or trivial)
- benchmark:  authority 1-10  (10=rigorous methodology, credible source, reproducible, 1=cherry-picked or unclear)
- tutorial:   practicality 1-10  (10=immediately actionable with working code/steps, 1=too abstract to use)

Items (with pre-classified types):
{items_with_types}
```

Output: updates `item.score`, `item.score_label`, and `item.category` (for research only).

### Pass 3 — Validate and keep/skip

One API call per batch. The LLM has full context (type + score) and makes the final keep/skip call:

```
You are reviewing LLM/AI content items for inclusion in a research vault.
Each item has been classified by type and scored on a type-appropriate axis.

For each item, output exactly one line:
<n>. keep|skip

Keep an item if it is genuinely worth a researcher reading and saving.
Skip an item if it is noise, too low-signal, or not relevant to LLM/AI work regardless of type.
Be selective but not overly conservative — a score of 6+ generally warrants keeping.

Items (with type and score):
{items_with_scores}
```

Output: sets `item.keep = True | False`. The scheduler/pipeline filters on `item.keep` instead of `item.novelty >= threshold`.

---

## Vault Output

### Directory structure

```
vault/strategies/
  research/       — one .md per research item
  releases/       — product/model/tool launches
  news/           — industry news and trends
  benchmarks/     — eval results and comparisons
  tutorials/      — how-tos and guides
  index.md        — auto-generated, grouped by type
```

`Writer.write_note()` routes to `strategies/<content_type>/` based on `item.content_type`.

### Note frontmatter

```yaml
---
title: "…"
date: YYYY-MM-DD
type: research             # content_type
score: 8                   # numeric score
score_label: novelty       # what the score means
category: architecture     # research sub-category; omitted for non-research
tags: [research, architecture, emerging]
validated: false
sources_count: 1
status: new
---
```

The `novelty:` field is replaced by `score:` + `score_label:`. Obsidian Dataview queries can filter on `type`, `score`, `score_label` directly.

### Index structure

`index.md` groups notes by content type, each section with type-appropriate column headers:

```markdown
# Strategy Index

## Research
| Title | Sub-category | Novelty | Validated |
…

## Releases
| Title | Significance | Validated |
…

## News
| Title | Timeliness | Date |
…

## Benchmarks
| Title | Authority | Validated |
…

## Tutorials
| Title | Practicality |
…
```

`Writer.regenerate_index()` reads `type:` and `score_label:` from frontmatter to group and label columns correctly.

---

## Files Changed

| File | Nature of change |
|---|---|
| `agent/models.py` | Add `content_type`, `score`, `score_label`, `keep`; remove `novelty`; default `category` to `""` |
| `agent/evaluator.py` | Replace single-pass prompt with three-pass pipeline; update parsing |
| `agent/writer.py` | Add type-based subdirectory routing; update note template; restructure `regenerate_index()` |
| `agent/scheduler.py` | Replace `novelty`-based filter with `item.keep` filter |
| `tests/test_evaluator.py` | Update for new fields and three-pass API call pattern |
| `tests/test_writer.py` | Update for subdirectory routing and new frontmatter |
| `tests/test_smoke.py` | Update fixture assertions for `score` / `content_type` |

---

## Out of Scope

- Changing the fetchers or sources — classification happens after fetch
- Retroactive re-classification of existing vault notes
- Per-type engagement thresholds (still a single global threshold in config)
- Obsidian Dataview plugin integration — vault is vanilla Obsidian-compatible markdown

---

## Open Questions

None — resolved in brainstorm.
