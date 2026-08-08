import pytest

from agent.canonical import canonical_id
from agent.models import RawItem


def _item(title="", url="", source="s"):
    return RawItem(title=title, body="", url=url, source=source, engagement=0, timestamp="2026-08-01")


@pytest.mark.parametrize("url", [
    "https://arxiv.org/abs/2410.12345",
    "https://arxiv.org/pdf/2410.12345",
    "https://arxiv.org/pdf/2410.12345v2",
    "https://huggingface.co/papers/2410.12345",
    "http://arxiv.org/abs/2410.12345v1",
])
def test_arxiv_id_from_url_shapes_strips_version(url):
    assert canonical_id(_item(url=url)) == "arxiv:2410.12345"


def test_arxiv_id_from_title_prefix():
    assert canonical_id(_item(title="[2410.12345] A New Attention Kernel", url="https://example.com/x")) == "arxiv:2410.12345"


def test_arxiv_beats_url_precedence():
    # arXiv id present in url -> arxiv scheme, not url scheme
    assert canonical_id(_item(url="https://arxiv.org/abs/2410.12345")).startswith("arxiv:")


def test_doi_from_url():
    assert canonical_id(_item(url="https://doi.org/10.1145/3597503.3639187")) == "doi:10.1145/3597503.3639187"


def test_doi_lowercased():
    assert canonical_id(_item(url="https://doi.org/10.1145/ABC.DEF")) == "doi:10.1145/abc.def"


def test_normalized_url_strips_scheme_www_query_fragment_trailing_slash():
    a = canonical_id(_item(url="https://www.Example.com/Path/?utm_source=x&ref=y#frag"))
    b = canonical_id(_item(url="http://example.com/Path"))
    assert a == b == "url:example.com/Path"


def test_normalized_url_keeps_case_of_path_but_lowercases_host():
    assert canonical_id(_item(url="https://EXAMPLE.com/AbC")) == "url:example.com/AbC"


def test_title_fallback_when_no_stable_url():
    # empty url -> title scheme, lowercased, punctuation stripped, whitespace collapsed
    got = canonical_id(_item(title="Kimi  K3:  A New!! Model", url=""))
    assert got == "title:kimi k3 a new model"


def test_title_fallback_when_url_is_non_http():
    assert canonical_id(_item(title="Some Release", url="mailto:x@y.com")).startswith("title:")
