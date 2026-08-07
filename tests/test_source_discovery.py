from agent.tools.source_discovery import SourceDiscovery


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
