"""ContentEnricher tests — full-text fetch + extraction with fail-soft fallback."""
from unittest.mock import MagicMock

from agent.enricher import ContentEnricher
from agent.models import RawItem


def _item(url="https://example.com/article", body="short snippet body"):
    return RawItem(
        title="Some Article",
        body=body,
        url=url,
        source="search/tavily",
        engagement=0,
        timestamp="2026-08-01",
    )


def test_generic_happy_path_replaces_body_and_marks_full(mocker):
    long_text = "A" * 1200
    resp = MagicMock()
    resp.headers = {"content-type": "text/html; charset=utf-8"}
    resp.text = "<html><body>irrelevant</body></html>"
    resp.raise_for_status = MagicMock()
    mocker.patch("agent.enricher.httpx.get", return_value=resp)
    mocker.patch("agent.enricher.trafilatura.extract", return_value=long_text)

    enricher = ContentEnricher(max_chars=500)
    item = enricher.enrich(_item())

    assert item.content_source == "full"
    assert item.body == "A" * 500  # capped at max_chars
    assert len(item.body) == 500


def test_arxiv_branch_uses_abstract(mocker):
    fake_result = MagicMock()
    fake_result.summary = "This is a clean arXiv abstract. " * 20
    fake_client = MagicMock()
    fake_client.results.return_value = iter([fake_result])
    mocker.patch("agent.enricher.arxiv.Search", return_value=MagicMock())
    mocker.patch("agent.enricher.arxiv.Client", return_value=fake_client)
    # httpx should NOT be called for arxiv
    spy_get = mocker.patch("agent.enricher.httpx.get")

    enricher = ContentEnricher(max_chars=8000)
    item = enricher.enrich(_item(url="https://arxiv.org/abs/2508.01234"))

    assert item.content_source == "full"
    assert "clean arXiv abstract" in item.body
    spy_get.assert_not_called()


def test_fetch_failure_keeps_snippet(mocker):
    mocker.patch("agent.enricher.httpx.get", side_effect=RuntimeError("boom"))
    enricher = ContentEnricher()
    original = "the original snippet"
    item = enricher.enrich(_item(body=original))
    assert item.body == original
    assert item.content_source == "snippet"


def test_short_extraction_falls_back_to_snippet(mocker):
    resp = MagicMock()
    resp.headers = {"content-type": "text/html"}
    resp.text = "<html></html>"
    resp.raise_for_status = MagicMock()
    mocker.patch("agent.enricher.httpx.get", return_value=resp)
    mocker.patch("agent.enricher.trafilatura.extract", return_value="tiny")  # < 400 chars

    enricher = ContentEnricher()
    original = "the original snippet"
    item = enricher.enrich(_item(body=original))
    assert item.body == original
    assert item.content_source == "snippet"


def test_non_html_content_type_falls_back(mocker):
    resp = MagicMock()
    resp.headers = {"content-type": "application/pdf"}
    resp.text = "%PDF-1.7 ..."
    resp.raise_for_status = MagicMock()
    mocker.patch("agent.enricher.httpx.get", return_value=resp)
    spy_extract = mocker.patch("agent.enricher.trafilatura.extract")

    enricher = ContentEnricher()
    original = "the original snippet"
    item = enricher.enrich(_item(body=original))
    assert item.body == original
    assert item.content_source == "snippet"
    spy_extract.assert_not_called()
