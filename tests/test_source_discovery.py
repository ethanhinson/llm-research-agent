import pytest
from unittest.mock import MagicMock

from agent.tools.source_discovery import SourceDiscovery


MOCK_SUGGESTIONS_RESPONSE = """\
Here are suggested new sources:
- r/LLMPrompting — focuses specifically on prompting techniques
- https://newsletter.example.com/feed.xml | AI Weekly | newsletter
"""


def test_source_discovery_returns_suggestions(mocker, tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n\n## Validated\n- r/LocalLLaMA\n")

    sd = SourceDiscovery(sources_path=sources_file, api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text=MOCK_SUGGESTIONS_RESPONSE)]
    mocker.patch.object(sd._client.messages, "create", return_value=mock_message)

    suggestions = sd.suggest(recent_titles=["Flash Attention 3", "Chain of Draft"])
    assert len(suggestions) > 0


def test_source_discovery_empty_when_no_new(mocker, tmp_path):
    sources_file = tmp_path / "sources.md"
    sources_file.write_text("# Sources\n")

    sd = SourceDiscovery(sources_path=sources_file, api_key="test-key")
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="No new sources to suggest at this time.")]
    mocker.patch.object(sd._client.messages, "create", return_value=mock_message)

    suggestions = sd.suggest(recent_titles=[])
    assert suggestions == []
