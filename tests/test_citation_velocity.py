import agent.tools.citation_velocity as cv


class _Resp:
    """Minimal httpx-style response stub for OpenAlex GET calls."""
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


def test_paper_id_from_arxiv_source_url():
    text = "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    assert cv.paper_ids_from_note(text) == "ARXIV:2410.12345"


def test_paper_id_from_doi_source_url():
    text = "## Sources\n- [P](https://doi.org/10.1145/abc.def) — s2 · 3\n"
    assert cv.paper_ids_from_note(text) == "DOI:10.1145/abc.def"


def test_paper_id_none_when_no_resolvable_id():
    text = "## Sources\n- [P](https://blog.example.com/x) — blog · 3\n"
    assert cv.paper_ids_from_note(text) is None


def test_paper_id_none_for_github_url_with_doi_like_segment():
    # a github URL containing a /10.NNNN/ path segment must NOT be read as a DOI.
    text = ("## Sources\n- [P](https://github.com/org/repo/releases/tag/v10.1234/final)"
            " — github · 3\n")
    assert cv.paper_ids_from_note(text) is None


def test_fetch_citation_counts_maps_batch_response(mocker):
    class Resp:
        status_code = 200
        def raise_for_status(self): pass
        def json(self):
            return [{"paperId": "a", "externalIds": {"ArXiv": "2410.12345"}, "citationCount": 42}]
    mocker.patch("agent.tools.citation_velocity.httpx.post", return_value=Resp())
    out = cv.fetch_citation_counts(["ARXIV:2410.12345"], api_key=None)
    assert out["ARXIV:2410.12345"] == 42


def test_fetch_citation_counts_429_then_skip_failsoft(mocker):
    class Resp429:
        status_code = 429
        def raise_for_status(self): pass
        def json(self): return []
    mocker.patch("agent.tools.citation_velocity.httpx.post", return_value=Resp429())
    mocker.patch("agent.tools.citation_velocity.time.sleep")
    assert cv.fetch_citation_counts(["ARXIV:2410.12345"], api_key=None) == {}


def test_run_flags_rising_and_stores_frontmatter(tmp_path, mocker):
    note = tmp_path / "strategies" / "research" / "n.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: \"P\"\ndate: 2026-08-01\ntype: research\nscore: 7\n"
        "score_label: novelty\ntags: [rag]\nvalidated: false\nsources_count: 1\n"
        "content_source: snippet\ncitation_count: 10\nstatus: new\n---\n\n# P\n\n"
        "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    )
    mocker.patch(
        "agent.tools.citation_velocity._citation_counts_for",
        return_value={"ARXIV:2410.12345": 40},
    )
    flagged = cv.run_citation_velocity(tmp_path, min_delta=25, api_key=None, today="2026-08-08")
    text = note.read_text()
    assert flagged == 1
    assert "citation_count: 40" in text
    assert "citation_delta: 30" in text
    assert "rising: true" in text
    assert "citation_checked: 2026-08-08" in text


def test_run_clears_stale_rising_when_no_longer_rising(tmp_path, mocker):
    """A note previously flagged rising: true whose re-poll delta falls below
    min_delta must have rising reset to false (not left stale)."""
    note = tmp_path / "strategies" / "research" / "n.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: \"P\"\ntype: research\ncitation_count: 100\nrising: true\n"
        "status: new\n---\n\n"
        "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    )
    mocker.patch(
        "agent.tools.citation_velocity._citation_counts_for",
        return_value={"ARXIV:2410.12345": 105},  # delta 5 < min_delta 25
    )
    flagged = cv.run_citation_velocity(tmp_path, min_delta=25, api_key=None, today="2026-08-08")
    text = note.read_text()
    assert flagged == 0
    assert "rising: false" in text
    assert "rising: true" not in text


def test_run_disabled_is_noop_via_delta_below_threshold(tmp_path, mocker):
    note = tmp_path / "strategies" / "research" / "n.md"
    note.parent.mkdir(parents=True)
    note.write_text(
        "---\ntitle: \"P\"\ntype: research\ncitation_count: 10\nstatus: new\n---\n\n"
        "## Sources\n- [P](https://arxiv.org/abs/2410.12345) — arxiv · 3\n"
    )
    mocker.patch(
        "agent.tools.citation_velocity._citation_counts_for",
        return_value={"ARXIV:2410.12345": 12},
    )
    flagged = cv.run_citation_velocity(tmp_path, min_delta=25, api_key=None, today="2026-08-08")
    assert flagged == 0
    assert "rising: true" not in note.read_text()


# --- Keyless OpenAlex source -----------------------------------------------


def test_openalex_doi_for_maps_arxiv_and_doi():
    assert cv._openalex_doi_for("ARXIV:2311.13165") == "10.48550/arxiv.2311.13165"
    assert cv._openalex_doi_for("DOI:10.1145/ABC.def") == "10.1145/abc.def"
    assert cv._openalex_doi_for("not-an-id") is None


def test_openalex_batch_doi_maps_counts(mocker):
    # OpenAlex returns the DOI in full https://doi.org/ form; we map it back.
    payload = {"results": [
        {"doi": "https://doi.org/10.48550/arxiv.2311.13165", "cited_by_count": 10},
    ]}
    get = mocker.patch("agent.tools.citation_velocity.httpx.get", return_value=_Resp(payload))
    out = cv.fetch_citation_counts_openalex([("ARXIV:2311.13165", "Multimodal LLMs: A Survey")])
    assert out == {"ARXIV:2311.13165": 10}
    # DOI hit resolves it — no title-search fallback call is made.
    assert get.call_count == 1


def test_openalex_title_fallback_on_doi_miss(mocker):
    batch_empty = {"results": []}
    title_hit = {"results": [{"title": "Attention Is All You Need", "cited_by_count": 6602}]}
    mocker.patch(
        "agent.tools.citation_velocity.httpx.get",
        side_effect=[_Resp(batch_empty), _Resp(title_hit)],
    )
    out = cv.fetch_citation_counts_openalex([("ARXIV:1706.03762", "Attention Is All You Need")])
    assert out == {"ARXIV:1706.03762": 6602}


def test_openalex_title_fallback_rejects_title_mismatch(mocker):
    batch_empty = {"results": []}
    wrong = {"results": [{"title": "A Completely Different Paper", "cited_by_count": 999}]}
    mocker.patch(
        "agent.tools.citation_velocity.httpx.get",
        side_effect=[_Resp(batch_empty), _Resp(wrong)],
    )
    out = cv.fetch_citation_counts_openalex([("ARXIV:1706.03762", "Attention Is All You Need")])
    assert out == {}


def test_openalex_failsoft_on_request_error(mocker):
    mocker.patch("agent.tools.citation_velocity.httpx.get", side_effect=RuntimeError("boom"))
    out = cv.fetch_citation_counts_openalex([("ARXIV:2311.13165", "X")])
    assert out == {}


def test_citation_source_defaults_to_openalex_without_key(mocker, monkeypatch):
    monkeypatch.delenv("S2_API_KEY", raising=False)
    oa = mocker.patch(
        "agent.tools.citation_velocity.fetch_citation_counts_openalex",
        return_value={"ARXIV:1": 5},
    )
    s2 = mocker.patch("agent.tools.citation_velocity.fetch_citation_counts", return_value={})
    notes = [("note", "text", "ARXIV:1", {"title": "T"})]
    out = cv._citation_counts_for(notes, api_key=None, mailto="me@example.com")
    assert out == {"ARXIV:1": 5}
    oa.assert_called_once()
    s2.assert_not_called()


def test_citation_source_uses_s2_when_key_present(mocker, monkeypatch):
    monkeypatch.setenv("S2_API_KEY", "secret")
    oa = mocker.patch("agent.tools.citation_velocity.fetch_citation_counts_openalex", return_value={})
    s2 = mocker.patch(
        "agent.tools.citation_velocity.fetch_citation_counts",
        return_value={"ARXIV:1": 9},
    )
    notes = [("note", "text", "ARXIV:1", {"title": "T"})]
    out = cv._citation_counts_for(notes, api_key=None, mailto=None)
    assert out == {"ARXIV:1": 9}
    s2.assert_called_once()
    oa.assert_not_called()
