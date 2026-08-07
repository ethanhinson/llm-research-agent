<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0006 — LLM-generated freeform topic tags](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0006-llm-topic-tags.md)**
<!-- docket:backlink:end -->

# LLM-Generated Topic Tags Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Plan authored in `auto` fallback.** The configured plan skill (`superpowers:writing-plans`) could not be invoked in this session, so the implementer authored this plan directly per the docket Skill-layer missing-skill rule (degrade to `auto` + warn). Format follows the writing-plans convention.

**Goal:** Add a fourth evaluator pass that generates 2–4 lowercase-hyphenated topic tags per item and appends them to the item's structural tags.

**Architecture:** A new `TAG_PROMPT` constant and `_tag_batch()` method on `Evaluator`, called after `_set_tags()` inside the existing `score()` per-batch loop. Tags are parsed from a numbered LLM response, normalized to lowercase-hyphenated tokens, capped at 4, and appended to `item.tags` (structural tags remain leading). No downstream writer/model/scheduler changes; retroactive reclassify inherits topic tags for free because it routes through `score()`.

**Tech Stack:** Python 3, `anthropic` SDK, `re`, pytest + pytest-mock (mocker).

## Global Constraints

- Topic tags: lowercase, hyphenated, no special characters; 2–4 per item; distinct from structural tags (no "research"/"release"/"news").
- Structural tag(s) always written first; topic tags appended after.
- Cap appended topic tags at 4 (`topic_tags[:4]`).
- No changes to `agent/writer.py`, `agent/models.py`, `agent/scheduler.py`, `agent/reclassifier.py`, or `agent/cli.py`.
- Run the suite via `uv run python -m pytest` after `uv sync --extra dev` — a bare `pytest` loads a crashing global deepeval pyenv-shim plugin (learnings: pytest-shim-and-venv-provisioning).
- Live Anthropic calls are unavailable (insufficient account credit → 400 credit-balance-too-low). All work and verification is mock-based per TDD; any live end-to-end tagging run is deferred.

---

### Task 1: `_tag_batch` topic-tag pass on the Evaluator

**Files:**
- Modify: `agent/evaluator.py` (add `TAG_PROMPT` constant near the other prompt constants; add `_tag_batch()` method; call it after `_set_tags(batch)` inside `score()`)
- Test: `tests/test_evaluator.py` (add new tag-pass tests; update the three existing full-`score()` tests to supply a 4th mock response)

**Interfaces:**
- Consumes: `RawItem.tags: list` (already populated with structural tags by `_set_tags`), `RawItem.content_type`, `RawItem.title`, `RawItem.body`; `Evaluator._call(prompt) -> str`.
- Produces: `Evaluator._tag_batch(self, batch: list[RawItem]) -> None` — mutates `batch[idx].tags` in place, appending up to 4 normalized topic tags; called inside `score()` after `_set_tags`.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_evaluator.py` (reuse the module's existing `make_item` / `_mock_message` helpers):

```python
def test_tag_batch_appends_to_structural_tags(mocker):
    evaluator = Evaluator(api_key="test-key")
    mocker.patch.object(
        evaluator._client.messages, "create",
        return_value=_mock_message("1. rag chain-of-thought\n2. fine-tuning rlhf\n"),
    )
    a, b = make_item("A"), make_item("B")
    a.tags = ["research", "agentic"]
    b.tags = ["release"]
    evaluator._tag_batch([a, b])
    assert a.tags == ["research", "agentic", "rag", "chain-of-thought"]
    assert b.tags == ["release", "fine-tuning", "rlhf"]


def test_tag_batch_caps_at_4_tags(mocker):
    evaluator = Evaluator(api_key="test-key")
    mocker.patch.object(
        evaluator._client.messages, "create",
        return_value=_mock_message("1. a b c d e f\n"),
    )
    item = make_item("A")
    item.tags = ["research"]
    evaluator._tag_batch([item])
    # 4 topic tags max appended, structural tag preserved leading
    assert item.tags == ["research", "a", "b", "c", "d"]


def test_tag_batch_normalizes_commas_and_case(mocker):
    evaluator = Evaluator(api_key="test-key")
    mocker.patch.object(
        evaluator._client.messages, "create",
        return_value=_mock_message("1. RAG, Fine Tuning, reasoning\n"),
    )
    item = make_item("A")
    item.tags = ["research"]
    evaluator._tag_batch([item])
    assert item.tags == ["research", "rag", "fine-tuning", "reasoning"]


def test_score_includes_topic_tags(mocker):
    evaluator = Evaluator(api_key="test-key")
    responses = [
        _mock_message("1. research\n"),
        _mock_message("1. 8 architecture\n"),
        _mock_message("1. keep\n"),
        _mock_message("1. rag reasoning\n"),
    ]
    mocker.patch.object(evaluator._client.messages, "create", side_effect=responses)
    items = [make_item("Flash Attention")]
    result = evaluator.score(items)
    assert result[0].tags[0] == "research"          # structural first
    assert "rag" in result[0].tags and "reasoning" in result[0].tags
```

Note on `test_tag_batch_caps_at_4_tags`: the cap is on *topic* tags appended (`topic_tags[:4]`), so a 1-structural + 4-topic result is 5 total. Assert accordingly.

- [ ] **Step 2: Update the three existing full-`score()` tests for the new 4th call**

`score()` now issues a 4th `_call` (tag pass). Each of these currently seeds `side_effect` with exactly 3 responses and will `StopIteration`. Append one tag-pass response to each list:
- `test_evaluator_three_passes_sets_fields`: append `_mock_message("1. flash-attention\n2. gpt\n")`.
- `test_evaluator_missing_classify_line_keeps_default`: append `_mock_message("1. reasoning\n")`.
- `test_evaluator_subcategory_only_set_for_research`: append `_mock_message("1. fine-tuning\n")`.

Their existing assertions are unchanged.

- [ ] **Step 3: Run the tests to verify they fail**

Run: `uv run python -m pytest tests/test_evaluator.py -v` (after `uv sync --extra dev`)
Expected: the new `test_tag_batch_*` / `test_score_includes_topic_tags` FAIL (`_tag_batch` not defined / topic tags absent). The three updated existing tests should already pass after Step 2's mock addition once `_tag_batch` exists — but before the implementation, `test_score_includes_topic_tags` and the new tag tests fail.

- [ ] **Step 4: Write the minimal implementation in `agent/evaluator.py`**

Add the constant alongside the other prompts:

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

Add the method (mirrors `_classify_batch`'s parse shape):

```python
def _tag_batch(self, batch: list[RawItem]):
    item_lines = "\n".join(
        f"{i+1}. [{item.content_type}] {item.title} — {item.body[:150]}"
        for i, item in enumerate(batch)
    )
    text = self._call(TAG_PROMPT.format(items=item_lines))
    pattern = re.compile(r"^\s*(\d+)\.\s+(.+)$", re.MULTILINE)
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

Wire it into `score()` after `_set_tags(batch)`:

```python
self._set_tags(batch)    # structural tags first
self._tag_batch(batch)   # topic tags appended
```

Note the parse subtlety: `re.split(r"[,\s]+", ...)` on `"RAG, Fine Tuning, reasoning"` after `.replace(" ", "-")` — verify the `test_tag_batch_normalizes_commas_and_case` expectation matches actual token boundaries; adjust the split/normalize order if "fine tuning" must become "fine-tuning" (split on commas first, then hyphenate intra-token spaces). Make the implementation satisfy the test, keeping normalization deterministic.

- [ ] **Step 5: Run the tests to verify they pass**

Run: `uv run python -m pytest tests/test_evaluator.py -v`
Expected: all evaluator tests PASS.

- [ ] **Step 6: Run the full suite (regression gate)**

Run: `uv run python -m pytest`
Expected: full suite green (prior baseline was 98 passed; new tests add to that). If any startup crash mentions `TracerProvider.get_tracer()` or `trafilatura`, that is environment pollution — re-provision with `uv sync --extra dev` and re-run; it is not a code failure.

- [ ] **Step 7: Commit**

Commit on `feat/llm-topic-tags` with a message describing the topic-tag pass.
