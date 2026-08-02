from dataclasses import dataclass, field


@dataclass
class RawItem:
    title: str
    body: str
    url: str
    source: str
    engagement: int
    timestamp: str
    novelty: int = 0
    validated: bool = False
    sources_count: int = 1
    category: str = "architecture"
    tags: list = field(default_factory=list)
