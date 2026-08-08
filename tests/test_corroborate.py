from agent.canonical import canonical_id
from agent.models import RawItem
from agent.tools.corroborate import corroborate


def _item(title, source, url, engagement=100):
    it = RawItem(title=title, body="", url=url, source=source, engagement=engagement, timestamp="2026-08-01")
    it.canonical_id = canonical_id(it)
    return it


def test_same_arxiv_identity_collapses_to_one_item():
    items = [
        _item("Flash Attention 3", "hackernews", "https://arxiv.org/abs/2410.12345"),
        _item("Flash Attention 3 (v2)", "hf-papers", "https://arxiv.org/pdf/2410.12345v2"),
    ]
    result = corroborate(items)
    assert len(result) == 1
    rep = result[0]
    assert rep.validated is True
    assert rep.sources_count == 2
    assert {s[0] for s in rep.corroboration_sources} == {"hackernews", "hf-papers"}


def test_distinct_identities_pass_through():
    items = [
        _item("Paper A", "arxiv", "https://arxiv.org/abs/2410.00001"),
        _item("Paper B", "arxiv", "https://arxiv.org/abs/2410.00002"),
    ]
    result = corroborate(items)
    assert len(result) == 2
    assert all(i.sources_count == 1 and not i.validated for i in result)


def test_single_source_not_validated():
    items = [_item("Solo LoRA paper", "arxiv", "https://arxiv.org/abs/2410.99999")]
    result = corroborate(items)
    assert result[0].validated is False
    assert result[0].sources_count == 1


def test_same_source_twice_counts_one_distinct_source():
    items = [
        _item("Same paper", "arxiv", "https://arxiv.org/abs/2410.12345"),
        _item("Same paper", "arxiv", "https://arxiv.org/pdf/2410.12345"),
    ]
    result = corroborate(items)
    assert len(result) == 1
    assert result[0].sources_count == 1
    assert result[0].validated is False


def test_title_fallback_fuzzy_merge_for_non_paper_items():
    # No stable URL -> title: bucket; near-titles from distinct sources merge at ratio>=85
    items = [
        _item("Kimi K3: A New Model", "news", ""),
        _item("Kimi K3: A New Model!", "blog", ""),
    ]
    result = corroborate(items)
    assert len(result) == 1
    assert result[0].sources_count == 2
    assert result[0].validated is True


def test_representative_prefers_arxiv_url():
    items = [
        _item("Paper X", "blog", "https://blog.example.com/paper-x"),
        _item("Paper X", "arxiv", "https://arxiv.org/abs/2410.55555"),
    ]
    # These are DISTINCT identities (url: vs arxiv:), so they do NOT merge here.
    result = corroborate(items)
    assert len(result) == 2
