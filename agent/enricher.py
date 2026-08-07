"""Full-text content enrichment.

Replaces a RawItem's snippet body with extracted full-page text when possible,
so the synthesizer has real article text to ground on. Fail-soft: any error,
non-HTML content, or too-thin extraction keeps the original snippet body and
leaves content_source == "snippet". enrich() never raises.
"""
import arxiv
import httpx
import trafilatura

from agent.models import RawItem

MIN_EXTRACT_CHARS = 400
DEFAULT_MAX_CHARS = 8000
FETCH_TIMEOUT = 15
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0 Safari/537.36"
)


def _is_arxiv(url: str) -> bool:
    return "arxiv.org/abs/" in url or "arxiv.org/pdf/" in url


def _arxiv_id(url: str) -> str:
    # https://arxiv.org/abs/2508.01234  ->  2508.01234
    # https://arxiv.org/pdf/2508.01234  ->  2508.01234
    tail = url.rstrip("/").split("/")[-1]
    return tail.removesuffix(".pdf")


class ContentEnricher:
    def __init__(self, max_chars: int = DEFAULT_MAX_CHARS):
        self.max_chars = max_chars

    def enrich(self, item: RawItem) -> RawItem:
        try:
            if _is_arxiv(item.url):
                text = self._fetch_arxiv_abstract(item.url)
            else:
                text = self._fetch_and_extract(item.url)
        except Exception as exc:  # fail-soft: keep snippet
            print(f"[warn] enrich failed for {item.url}: {exc}")
            text = None

        if text and len(text) >= MIN_EXTRACT_CHARS:
            item.body = text[: self.max_chars]
            item.content_source = "full"
        # else: leave body + content_source untouched (stays "snippet")
        return item

    def enrich_all(self, items: list[RawItem]) -> list[RawItem]:
        for item in items:
            try:
                self.enrich(item)
            except Exception as exc:  # defensive; enrich is already fail-soft
                print(f"[warn] enrich_all skipped {item.url}: {exc}")
        return items

    def _fetch_arxiv_abstract(self, url: str) -> str | None:
        arxiv_id = _arxiv_id(url)
        search = arxiv.Search(id_list=[arxiv_id])
        client = arxiv.Client()
        for result in client.results(search):
            return (result.summary or "").strip()
        return None

    def _fetch_and_extract(self, url: str) -> str | None:
        resp = httpx.get(
            url,
            timeout=FETCH_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        content_type = resp.headers.get("content-type", "")
        if "html" not in content_type.lower():
            return None
        extracted = trafilatura.extract(resp.text)
        return extracted
