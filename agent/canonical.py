"""Canonical item identity — the dedup + corroboration key.

Pure and dependency-free. Precedence: arXiv id > DOI > normalized URL >
normalized title. `title:` is the fallback for items with no stable URL
(some releases / news).
"""

import re

from agent.models import RawItem

_ARXIV_URL = re.compile(
    r"(?:arxiv\.org/(?:abs|pdf)/|huggingface\.co/papers/)(\d{4}\.\d{4,5})(?:v\d+)?",
    re.IGNORECASE,
)
_ARXIV_TITLE = re.compile(r"^\s*\[(\d{4}\.\d{4,5})(?:v\d+)?\]")
_DOI = re.compile(r"(10\.\d{4,9}/[^\s?#]+)")
_TRACKING = re.compile(r"^(utm_.*|ref)$", re.IGNORECASE)


def _arxiv_id(item: RawItem) -> str:
    m = _ARXIV_URL.search(item.url or "")
    if m:
        return m.group(1)
    m = _ARXIV_TITLE.match(item.title or "")
    if m:
        return m.group(1)
    return ""


def _doi(url: str) -> str:
    m = _DOI.search(url or "")
    return m.group(1).lower() if m else ""


def _normalized_url(url: str) -> str:
    u = (url or "").strip()
    u = re.sub(r"^[a-zA-Z][a-zA-Z0-9+.\-]*://", "", u)  # drop scheme
    u = u.split("#", 1)[0]                               # drop fragment
    path_part, _, query = u.partition("?")
    # drop tracking params but keep meaningful ones
    if query:
        kept = [
            kv for kv in query.split("&")
            if kv and not _TRACKING.match(kv.split("=", 1)[0])
        ]
        if kept:
            path_part = path_part + "?" + "&".join(kept)
    if path_part.lower().startswith("www."):
        path_part = path_part[4:]
    host, sep, rest = path_part.partition("/")
    host = host.lower()
    normalized = host + sep + rest
    normalized = normalized.rstrip("/")
    return normalized


def _normalized_title(title: str) -> str:
    t = (title or "").lower()
    t = re.sub(r"[^a-z0-9\s]", "", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def canonical_id(item: RawItem) -> str:
    arxiv = _arxiv_id(item)
    if arxiv:
        return f"arxiv:{arxiv}"
    doi = _doi(item.url)
    if doi:
        return f"doi:{doi}"
    url = item.url or ""
    if re.match(r"^https?://", url, re.IGNORECASE):
        norm = _normalized_url(url)
        if norm:
            return f"url:{norm}"
    return f"title:{_normalized_title(item.title)}"
