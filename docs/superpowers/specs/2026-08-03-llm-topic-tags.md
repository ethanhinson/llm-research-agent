<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0006 — LLM-generated freeform topic tags](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0006-llm-topic-tags.md)**
<!-- docket:backlink:end -->

# LLM-Generated Topic Tags — Design Spec

**Date:** 2026-08-03
**Status:** Approved

---

## Overview

Extend the evaluator with a fourth pass that generates 2–4 freeform topic tags per item. These run after the structural tags (`_set_tags()`) and are appended to `item.tags`. The Obsidian tag pane then becomes browseable by topic (e.g. `#rag`, `#fine-tuning`, `#safety-alignment`) in addition to structure (`#research`, `#release`).

---

## Tag Format

- Lowercase, hyphenated, no special characters: `rag`, `chain-of-thought`, `inference-efficiency`
- 2–4 tags per item (the LLM is instructed to be specific and non-redundant)
- Topic tags are distinct from structural tags — they describe *what the content is about*, not what *type* it is
- The structural tag(s) are always written first: `[research, agentic, chain-of-thought, reasoning]`

### Suggested vocabulary (guidance in prompt, not an exhaustive whitelist)

`rag`, `fine-tuning`, `inference-efficiency`, `chain-of-thought`, `reasoning`, `multimodal`, `safety-alignment`, `tool-use`, `agent-frameworks`, `context-window`, `embeddings`, `instruction-following`, `code-generation`, `vision`, `long-context`, `speculative-decoding`, `memory`, `rlhf`, `synthetic-data`, `evaluation`

The prompt should encourage the model to coin new tags when none of the above fit, as long as they follow the lowercase-hyphenated convention.

---

## Evaluator Changes

### New constant

```python
TAG_PROMPT = """\
You are tagging LLM/AI content items with topic tags for an Obsidian research vault.

For each item, output exactly one line:
<n>. tag1 tag2 tag3

Rules:
- 2 to 4 tags per item
- Lowercase, hyphenated (rag, chain-of-thought, fine-tuning)
- Tags describe the topic, NOT the content type (no "research", "news", "release")
- Be specific: prefer "speculative-decoding" over "inference", "rlhf" over "training"
- Non-redundant: don't emit both "reasoning" and "chain-of-thought" for the same item

Common topics (not exhaustive — coin new ones when needed):
rag fine-tuning inference-efficiency chain-of-thought reasoning multimodal
safety-alignment tool-use agent-frameworks context-window embeddings
instruction-following code-generation vision long-context speculative-decoding
memory rlhf synthetic-data evaluation

Items:
{items}"""
```

### New method

```python
def _tag_batch(self, batch: list[RawItem]):
    item_lines = "\n".join(
        f"{i+1}. [{item.content_type}] {item.title} — {item.body[:150]}"
        for i, item in enumerate(batch)
    )
    text = self._call(TAG_PROMPT.format(items=item_lines))
    pattern = re.compile(
        r"^\s*(\d+)\.\s+(.+)$",
        re.MULTILINE,
    )
    for match in pattern.finditer(text):
        idx = int(match.group(1)) - 1
        if 0 <= idx < len(batch):
            raw_tags = match.group(2).strip()
            topic_tags = [
                t.strip().lower().replace(" ", "-")
                for t in re.split(r"[,\s]+", raw_tags)
                if t.strip()
            ]
            batch[idx].tags = batch[idx].tags + topic_tags[:4]
```

### Updated `score()` call order

```python
def score(self, items: list[RawItem]) -> list[RawItem]:
    if not items:
        return []
    for batch_start in range(0, len(items), BATCH_SIZE):
        batch = items[batch_start: batch_start + BATCH_SIZE]
        self._classify_batch(batch)
        self._score_batch(batch)
        self._validate_batch(batch)
        self._set_tags(batch)    # structural tags first
        self._tag_batch(batch)   # topic tags appended
    return items
```

---

## No Changes Required

- `agent/writer.py` — already does `", ".join(item.tags)`, handles any length
- `agent/models.py` — `tags: list` field already exists
- `agent/scheduler.py` — no changes; evaluator is called as before
- `vault/index.md` — the index doesn't render tags, so no index changes

---

## Tests

### `tests/test_evaluator.py`

- `test_tag_batch_appends_to_structural_tags`: mock `_call` to return `"1. rag chain-of-thought\n2. fine-tuning rlhf"`. Verify that after `_tag_batch`, items with `tags=["research", "agentic"]` become `["research", "agentic", "rag", "chain-of-thought"]`.
- `test_tag_batch_caps_at_4_tags`: if the LLM returns 5+ tags, only the first 4 are appended.
- `test_tag_batch_normalizes_commas`: handles comma-separated output like `"rag, fine-tuning, reasoning"`.
- `test_score_includes_topic_tags`: end-to-end mock of `score()` verifying topic tags present on items.

---

## Token Budget

Each batch of 20 items × 150 chars ≈ 3000 input tokens per batch. The tag response is short (≈100 tokens per batch). The fourth API call per batch adds ~10% to evaluator cost — acceptable for Haiku pricing.

---

## Future: Reclassify Integration

Once change 0005 lands, the `cmd_reclassify` function should also call `_tag_batch()` so that retroactively reclassified notes also receive topic tags. This is noted as a follow-up scope extension in change 0005.
