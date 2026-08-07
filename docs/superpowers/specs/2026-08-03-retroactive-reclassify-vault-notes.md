<!-- docket:backlink:start (generated — do not hand-edit) -->
> ↩ **[Change 0005 — Retroactive re-classification of existing vault notes](https://github.com/ethanhinson/llm-research-agent/blob/docket/docs/changes/archive/2026-08-07-0005-retroactive-reclassify-vault-notes.md)**
<!-- docket:backlink:end -->

# Retroactive Re-classification of Vault Notes — Design Spec

**Date:** 2026-08-03
**Status:** Approved

---

## Overview

Before the three-pass evaluator shipped (change 0004), the pipeline had no content-type system. This change adds a `cli.py reclassify` command to retroactively type and file pre-type-system notes.

**Reconcile note (2026-08-07):** the original premise ("~51 Aug 1 notes in `strategies/research/`") is stale. The actual target set is **167 flat top-level notes** at `vault/strategies/*.md` (dated 2026-08-03/04/05), written under the OLD schema — `category:` + `novelty:` frontmatter, **no `type:` field**, never filed into a type subdir. The 156 notes already in the `research/`/`releases/`/`news/`/`benchmarks/`/`tutorials/` subdirs already carry the new schema. Reclassify targets the flat notes: type them, rewrite to the new schema, and move them into the correct subdir.

---

## New CLI Command

```
python cli.py reclassify [--date YYYY-MM-DD] [--all]
```

- `--date YYYY-MM-DD`: re-classify only notes whose filename starts with that date (default: yesterday)
- `--all`: re-classify every note in every subdirectory

### Flow

1. Collect target `.md` files from `vault/strategies/**/*.md` (filtered by date prefix if `--date` given; `--all` = every note). Recursive glob covers both flat top-level notes and subdir notes.
2. Parse each file with `agent.regenerator.split_note(content) -> (fm, body)` (reused helper)
3. Build a `RawItem` per note. Read defensively across old + new schema: `title=fm.get("title", path.stem)`, `body=<note body text>`, `url=<first ## Sources url or "">`, `source=fm.get("source", "")`, `engagement=0`, `timestamp=fm.get("date", "")`. (Old-schema notes lack `type`/`score`/`score_label`; those are set by the evaluator, so absence is fine.)
4. Run the batch through `Evaluator.score()` (all three passes: classify, score, validate — plus `_set_tags`)
5. For each note, rewrite frontmatter fields: `type`, `score`, `score_label`, `category` (research only — remove the key otherwise), `tags`. Drop the old `novelty:` key.
6. Move the file to the correct subdir (`strategies/<TYPE_DIRS[item.content_type]>/`). A flat top-level note always moves; a subdir note whose type is unchanged stays put.
7. After all notes are processed, call `Writer(vault_path).regenerate_index()`

### Key implementation notes

- The reclassify command does **not** touch the deduplicator index — reclassification is a metadata update, not a new item ingest
- `item.keep` from the validate pass is informational only here — we re-classify regardless of keep/skip (the note already exists; we're not deciding whether to save it)
- If a filename collision occurs on move (rare: two notes with identical slugs), append a `-2` suffix rather than overwriting
- The command follows the `cmd_regenerate(args, cfg)` + `_build_regenerate_parser(subparsers)` shape and is dispatched by the explicit if/elif chain in `main()`. The codebase does NOT use `set_defaults(func=...)`.
- Print a summary at the end: `N notes reclassified, M moved, K errored`

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

Follow the `cmd_regenerate` / `_build_regenerate_parser` pattern (change 0007). Add a `_build_reclassify_parser(subparsers)` builder, call it in `main()`, and add a `reclassify` branch to the if/elif dispatch:

```python
def _build_reclassify_parser(subparsers):
    p = subparsers.add_parser("reclassify", help="Re-classify existing vault notes")
    p.add_argument("--date", default=None, help="Only notes from this date (YYYY-MM-DD)")
    p.add_argument("--all", action="store_true", help="Re-classify all notes")
    return p

# in main():
_build_reclassify_parser(sub)
...
elif args.command == "reclassify":
    cmd_reclassify(args, cfg)
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
