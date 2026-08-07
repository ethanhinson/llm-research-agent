from agent.tools.source_discovery import SourceDiscovery, append_suggestions


MOCK_SUGGESTIONS_RESPONSE = """\
Here are suggested new sources:
- r/LLMPrompting — focuses specifically on prompting techniques
- https://newsletter.example.com/feed.xml | AI Weekly | newsletter
"""


class FakeLLM:
    def __init__(self, text=""):
        self.text = text

    def complete(self, prompt, max_tokens):
        return self.text


def test_source_discovery_returns_suggestions(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n\n## Validated\n- r/LocalLLaMA\n")

    fake = FakeLLM(MOCK_SUGGESTIONS_RESPONSE)
    sd = SourceDiscovery(sources_path=sources_file, client=fake)

    suggestions = sd.suggest(recent_titles=["Flash Attention 3", "Chain of Draft"])
    assert len(suggestions) > 0


def test_source_discovery_empty_when_no_new(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n")

    fake = FakeLLM("No new sources to suggest at this time.")
    sd = SourceDiscovery(sources_path=sources_file, client=fake)

    suggestions = sd.suggest(recent_titles=[])
    assert suggestions == []


# --- append_suggestions (change 0010) ---------------------------------------


def test_append_suggestions_adds_dated_section(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n\n## Validated\n- r/LocalLLaMA\n")

    added = append_suggestions(
        sources_file,
        ["r/LLMPrompting — prompting techniques", "https://ex.com/feed | AI Weekly | newsletter"],
        date="2026-08-07",
    )

    text = sources_file.read_text()
    assert "## Suggested (pending review)" in text
    assert "2026-08-07" in text
    assert "r/LLMPrompting" in text
    assert added == 2


def test_append_suggestions_dedups_against_existing_feeds(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text(
        "# Sources\n\n## Validated\n"
        "- Simon Willison's blog (https://simonwillison.net/atom/everything/)\n"
    )

    # A suggestion pointing at an already-tracked URL is dropped.
    added = append_suggestions(
        sources_file,
        ["https://simonwillison.net/atom/everything/ | Simon | blog", "r/NewOne — fresh"],
        date="2026-08-07",
    )
    text = sources_file.read_text()
    assert added == 1
    assert "r/NewOne" in text
    # Not appended a second time under Suggested.
    assert text.count("simonwillison.net/atom/everything/") == 1


def test_append_suggestions_is_idempotent(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n")

    append_suggestions(sources_file, ["r/LLMPrompting — techniques"], date="2026-08-07")
    first = sources_file.read_text()
    added_again = append_suggestions(
        sources_file, ["r/LLMPrompting — techniques"], date="2026-08-08"
    )
    second = sources_file.read_text()

    assert added_again == 0
    assert second.count("r/LLMPrompting") == 1
    # The already-present suggestion is not re-appended.
    assert first.count("r/LLMPrompting") == second.count("r/LLMPrompting")


def test_append_suggestions_whole_line_dedup_not_substring(tmp_path):
    # A short non-URL suggestion that is a *substring* of an existing line must
    # NOT be dropped — dedup is whole-line, not a substring scan.
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n\n## Validated\n- r/LLMPrompting — techniques\n")

    added = append_suggestions(sources_file, ["r/LLM — general LLM subreddit"], date="2026-08-07")
    assert added == 1
    assert "r/LLM — general LLM subreddit" in sources_file.read_text()


def test_append_suggestions_empty_list_is_noop(tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n")
    original = sources_file.read_text()

    added = append_suggestions(sources_file, [], date="2026-08-07")
    assert added == 0
    assert sources_file.read_text() == original
