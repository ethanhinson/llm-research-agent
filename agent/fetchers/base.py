"""Source intake abstraction.

A single ``SourceAdapter`` protocol unifies every article-intake source behind a
``fetch() -> list[RawItem]`` seam (the same protocol-plus-factory idiom as the
``LLMClient`` abstraction, ADR-0001). Each adapter owns its own engagement
policy — the sweeps no longer carry stringly-typed engagement allowlists.
"""

from typing import Protocol, runtime_checkable

from agent.models import RawItem


@runtime_checkable
class SourceAdapter(Protocol):
    """An article-intake source.

    ``name`` is the source *family* id (e.g. ``"hackernews"``, ``"arxiv"``,
    ``"web"``, ``"search"``); individual items may carry a finer per-item
    ``RawItem.source`` (e.g. ``"web/<feed>"``, ``"search/<backend>"``).

    ``fetch`` returns already-engagement-filtered items — an adapter applies its
    own threshold, so the sweep-level pipeline never re-filters by source.
    """

    name: str

    def fetch(self) -> list[RawItem]: ...
