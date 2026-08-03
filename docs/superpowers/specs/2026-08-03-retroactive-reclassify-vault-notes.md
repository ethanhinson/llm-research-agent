<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0005 — Retroactive re-classification of existing vault notes](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/active/0005-retroactive-reclassify-vault-notes.md)**
<!-- docket:backlink:end -->

# Retroactive Re-classification of Vault Notes — Design Spec

**Date:** 2026-08-03
**Status:** Approved

---

## Overview

Before the three-pass evaluator shipped (change 0004), the pipeline had no content-type system — everything was classified as `research`. The vault currently has ~51 Aug 1 notes all sitting in `strategies/research/` with `type: research`, many of which are actually releases, news items, benchmarks, or tutorials. This change adds a `cli.py reclassify` command to fix them.

---

## New CLI Command

```
python cli.py reclassify [--date YYYY-MM-DD] [--all]
```

- `--date YYYY-MM-DD`: re-classify only notes whose filename starts with that date (default: yesterday)
- `--all`: re-classify every note in every subdirectory

### Flow

1. Collect target `.md` files from `vault/strategies/**/*.md` (filtered by date prefix if `--date` given)
2. Parse each file's YAML frontmatter: extract `title`, and use the body (everything after `---`) as `body`
3. Build a minimal `RawItem` per note: `title=fm["title"]`, `body=<note body>`, `url=fm.get("url", "")`, `source=fm.get("source", "")`, `engagement=0`, `timestamp=fm.get("date", "")`
4. Run the batch through `Evaluator.score()` (all three passes: classify, score, validate)
5. For each note, update frontmatter fields: `type`, `score`, `score_label`, `category` (research only), `tags`
6. If `item.content_type` differs from the old `type`, move the file to the correct subdir (`strategies/<TYPE_DIRS[item.content_type]>/`)
7. After all notes are processed, call `writer.regenerate_index()`

### Key implementation notes

- The reclassify command does **not** touch the deduplicator index — reclassification is a metadata update, not a new item ingest
- `item.keep` from the validate pass is informational only here — we re-classify regardless of keep/skip (the note already exists; we're not deciding whether to save it)
- If a filename collision occurs on move (rare: two notes with identical slugs), append a `-2` suffix rather than overwriting
- Print a summary at the end: `N notes reclassified, M moved, K unchanged`

---

## Frontmatter Update Logic

Read the existing frontmatter block, update these fields, write back:

```yaml
type: <new content_type>
score: <new score>
score_label: <new score_label>
category: <subcategory if research, else remove field>
tags: [<new tags>]
```

Leave all other frontmatter fields untouched (`title`, `date`, `validated`, `sources_count`, `status`, `url`, `source`).

---

## CLI Integration

Add `reclassify` to the argparse subcommands in `cli.py`:

```python
sub = subparsers.add_parser("reclassify", help="Re-classify existing vault notes")
sub.add_argument("--date", help="Only notes from this date (YYYY-MM-DD)")
sub.add_argument("--all", action="store_true", help="Re-classify all notes")
sub.set_defaults(func=cmd_reclassify)
```

---

## Tests

- `test_reclassify_updates_frontmatter`: mock evaluator to return `content_type="release"`, verify frontmatter is updated
- `test_reclassify_moves_file`: when type changes from `research` to `release`, verify file is moved to `releases/`
- `test_reclassify_no_move_when_type_unchanged`: when type stays `research`, file stays in `research/`
- `test_reclassify_regenerates_index`: verify `regenerate_index()` is called after processing

---

## Out of Scope

- Re-running the `keep/skip` validation to retroactively remove notes from the vault — reclassification only, not curation
- Updating the deduplicator index (URL-keyed; re-classification doesn't change URLs)
- Handling notes written by the search sweep with missing `url` frontmatter (they have `url:` from the writer template)
