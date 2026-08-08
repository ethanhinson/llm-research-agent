"""Intra-sweep collapse + corroboration — supersedes cross_validate.

Group items by canonical_id; return one representative per identity with
sources_count (distinct sources) and validated (>=2). For the title:-fallback
bucket only, a secondary fuzzy merge (ratio>=85) groups near-title non-paper
items so they still corroborate (no regression vs the old cross_validate).
"""

from thefuzz import fuzz

from agent.models import RawItem

TITLE_FUZZY_THRESHOLD = 85


def _pick_representative(group: list[RawItem]) -> RawItem:
    for it in group:
        if (it.canonical_id or "").startswith(("arxiv:", "doi:")):
            return it
    return group[0]


def _finalize(group: list[RawItem]) -> RawItem:
    rep = _pick_representative(group)
    distinct_sources = {it.source for it in group}
    rep.sources_count = len(distinct_sources)
    rep.validated = rep.sources_count >= 2
    seen = set()
    tuples = []
    for it in group:
        key = (it.source, it.url)
        if key in seen:
            continue
        seen.add(key)
        tuples.append((it.source, it.url, it.engagement))
    rep.corroboration_sources = tuples
    return rep


def corroborate(items: list[RawItem]) -> list[RawItem]:
    exact: dict[str, list[RawItem]] = {}
    title_bucket: list[RawItem] = []
    for it in items:
        cid = it.canonical_id or ""
        if cid.startswith("title:"):
            title_bucket.append(it)
        else:
            exact.setdefault(cid, []).append(it)

    # Secondary fuzzy merge inside the title: bucket only.
    title_groups: list[list[RawItem]] = []
    for it in title_bucket:
        placed = False
        for grp in title_groups:
            if fuzz.ratio(it.title.lower(), grp[0].title.lower()) >= TITLE_FUZZY_THRESHOLD:
                grp.append(it)
                placed = True
                break
        if not placed:
            title_groups.append([it])

    result: list[RawItem] = []
    for group in exact.values():
        result.append(_finalize(group))
    for group in title_groups:
        result.append(_finalize(group))
    return result
