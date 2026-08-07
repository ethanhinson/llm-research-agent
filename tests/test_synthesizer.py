"""NoteSynthesizer tests — Haiku section synthesis with fail-soft fallback."""
from agent.models import RawItem
from agent.synthesizer import NoteSynthesizer


class FakeLLM:
    """Injectable LLMClient stub. `complete` returns canned text or raises."""

    def __init__(self, text="", *, error=None):
        self.text = text
        self.error = error
        self.prompts = []

    def complete(self, prompt, max_tokens):
        self.prompts.append(prompt)
        if self.error is not None:
            raise self.error
        return self.text


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


def test_prompt_assembly_includes_title_and_body():
    fake = FakeLLM(WELL_FORMED)
    synth = NoteSynthesizer(client=fake)
    synth.synthesize(_item())

    prompt = fake.prompts[0]
    assert "Mixture of Experts explained" in prompt
    assert "MoE routes tokens" in prompt
    assert "research" in prompt


def test_well_formed_response_parses_three_sections():
    fake = FakeLLM(WELL_FORMED)
    synth = NoteSynthesizer(client=fake)
    sections = synth.synthesize(_item())
    assert set(sections.keys()) >= {"summary", "how_it_works", "why_it_matters"}
    assert "routes each token" in sections["summary"]
    assert "gating network" in sections["how_it_works"]
    assert "serving cost" in sections["why_it_matters"]


def test_api_failure_returns_empty_no_raise():
    fake = FakeLLM(error=RuntimeError("api down"))
    synth = NoteSynthesizer(client=fake)
    sections = synth.synthesize(_item())
    assert sections == {}


def test_partial_response_returns_what_parsed():
    partial = "SUMMARY:\nJust a summary, nothing else.\n"
    fake = FakeLLM(partial)
    synth = NoteSynthesizer(client=fake)
    sections = synth.synthesize(_item())
    assert sections.get("summary", "").strip() == "Just a summary, nothing else."
    # missing sections are absent or empty — writer falls back for those
    assert not sections.get("how_it_works")
    assert not sections.get("why_it_matters")
