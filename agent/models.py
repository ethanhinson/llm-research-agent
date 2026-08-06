from dataclasses import dataclass, field


@dataclass
class RawItem:
    title: str
    body: str
    url: str
    source: str
    engagement: int
    timestamp: str
    content_type: str = "research"   # research | release | news | benchmark | tutorial
    score: int = 0                   # meaning depends on content_type
    score_label: str = "novelty"     # novelty | significance | timeliness | authority | practicality
    keep: bool = False               # LLM's explicit keep/skip decision
    validated: bool = False
    sources_count: int = 1
    category: str = ""               # research sub-category only; empty for other types
    tags: list = field(default_factory=list)
    content_source: str = "snippet"  # snippet | full — where the note body text came from
