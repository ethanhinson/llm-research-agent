"""NoteSynthesizer tests — Haiku section synthesis with fail-soft fallback."""
from unittest.mock import MagicMock

from agent.models import RawItem
from agent.synthesizer import NoteSynthesizer


def _item(**kw):
    base = dict(
        title="Mixture of Experts explained",
        body="MoE routes tokens to specialist sub-networks, activating only a few per token.",
        url="https://example.com/moe",
        source="search/tavily",
        engagement=120,
        timestamp="2026-08-01",
        content_type="research",
        score=8,
        score_label="novelty",
        validated=True,
    )
    base.update(kw)
    return RawItem(**base)


def _mock_message(text):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


WELL_FORMED = """\
SUMMARY:
Mixture of Experts (MoE) is an architecture that routes each token to a small
subset of expert sub-networks. The key result is far lower compute per token.

HOW IT WORKS:
A gating network scores experts per token and activates the top-k. Only those
experts run, so a large parameter count costs little at inference time.

WHY IT MATTERS:
Practitioners get large-model quality at a fraction of the serving cost, which
is why frontier labs increasingly ship MoE models.
"""


def test_prompt_assembly_includes_title_and_body(mocker):
    synth = NoteSynthesizer(api_key="test-key")
    captured = {}

    def fake_create(**kwargs):
        captured["prompt"] = kwargs["messages"][0]["content"]
        return _mock_message(WELL_FORMED)

    mocker.patch.object(synth._client.messages, "create", side_effect=fake_create)
    synth.synthesize(_item())

    prompt = captured["prompt"]
    assert "Mixture of Experts explained" in prompt
    assert "MoE routes tokens" in prompt
    assert "research" in prompt


def test_well_formed_response_parses_three_sections(mocker):
    synth = NoteSynthesizer(api_key="test-key")
    mocker.patch.object(
        synth._client.messages, "create", return_value=_mock_message(WELL_FORMED)
    )
    sections = synth.synthesize(_item())
    assert set(sections.keys()) >= {"summary", "how_it_works", "why_it_matters"}
    assert "routes each token" in sections["summary"]
    assert "gating network" in sections["how_it_works"]
    assert "serving cost" in sections["why_it_matters"]


def test_api_failure_returns_empty_no_raise(mocker):
    synth = NoteSynthesizer(api_key="test-key")
    mocker.patch.object(
        synth._client.messages, "create", side_effect=RuntimeError("api down")
    )
    sections = synth.synthesize(_item())
    assert sections == {}


def test_partial_response_returns_what_parsed(mocker):
    synth = NoteSynthesizer(api_key="test-key")
    partial = "SUMMARY:\nJust a summary, nothing else.\n"
    mocker.patch.object(
        synth._client.messages, "create", return_value=_mock_message(partial)
    )
    sections = synth.synthesize(_item())
    assert sections.get("summary", "").strip() == "Just a summary, nothing else."
    # missing sections are absent or empty — writer falls back for those
    assert not sections.get("how_it_works")
    assert not sections.get("why_it_matters")
