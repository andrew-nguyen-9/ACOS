"""U8 — MBA Resume Corpus Scraper (opt-in only).

Fetches public resume bullet examples from MBA career portal pages.
- Respects robots.txt
- Rate-limits to 1 request per 5 seconds per domain
- Loads results into ChromaDB acos_bullet_examples
- Never runs during normal operation; must be explicitly triggered via POST /strategy/enrich-corpus
"""
from __future__ import annotations

import hashlib
import logging
import re
import time
from collections import defaultdict
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_RATE_LIMIT_SECONDS = 5.0
_MAX_BULLETS_PER_URL = 30
_BULLET_PATTERN = re.compile(r"^[•\-\*➤▶→]\s*(.+)", re.MULTILINE)
_MIN_BULLET_LEN = 40
_MAX_BULLET_LEN = 250

COLLECTION_NAME = "acos_bullet_examples"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _extract_bullets(html: str) -> list[str]:
    from html.parser import HTMLParser

    class _TextExtractor(HTMLParser):
        def __init__(self) -> None:
            super().__init__()
            self.chunks: list[str] = []
            self._skip = False

        def handle_starttag(self, tag: str, attrs: list) -> None:
            self._skip = tag in {"script", "style", "nav", "header", "footer"}

        def handle_endtag(self, tag: str) -> None:
            self._skip = False

        def handle_data(self, data: str) -> None:
            if not self._skip:
                self.chunks.append(data)

    extractor = _TextExtractor()
    extractor.feed(html)
    text = "\n".join(extractor.chunks)

    bullets: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if _MIN_BULLET_LEN <= len(line) <= _MAX_BULLET_LEN:
            # Heuristic: starts with action verb (capital letter)
            if line and line[0].isupper() and " " in line:
                bullets.append(line)
        # Also match explicit bullet characters
        m = _BULLET_PATTERN.match(line)
        if m:
            b = m.group(1).strip()
            if _MIN_BULLET_LEN <= len(b) <= _MAX_BULLET_LEN:
                bullets.append(b)

    return bullets[:_MAX_BULLETS_PER_URL]


class CorpusScraper:
    def __init__(self, chroma_client: Any) -> None:
        self._chroma = chroma_client
        self._last_request: dict[str, float] = defaultdict(float)

    def enrich(self, urls: list[str], max_per_domain: int = 5) -> dict:
        try:
            import requests  # type: ignore[import]
            import ollama as _ollama  # type: ignore[import]
        except ImportError as exc:
            return {"error": f"Missing dependency: {exc}", "bullets_added": 0}

        col = self._chroma.get_or_create_collection(COLLECTION_NAME)
        existing_ids: set[str] = set(col.get(include=[])["ids"])

        bullets_added = 0
        urls_processed = 0
        urls_failed: list[str] = []
        domain_counts: dict[str, int] = defaultdict(int)

        for url in urls:
            domain = _domain(url)
            if domain_counts[domain] >= max_per_domain:
                logger.info("Skipping %s — domain limit reached", url)
                continue

            self._rate_limit(domain)

            try:
                if not self._check_robots(url, requests):
                    logger.info("robots.txt disallows %s", url)
                    urls_failed.append(url)
                    continue

                resp = requests.get(url, timeout=10, headers={"User-Agent": "ACOS-research-bot/1.0"})
                resp.raise_for_status()
                bullets = _extract_bullets(resp.text)
                urls_processed += 1
                domain_counts[domain] += 1

                new_bullets = [b for b in bullets if _sha256(b) not in existing_ids]
                for b in new_bullets:
                    bid = _sha256(b)
                    embedding = _ollama.embeddings(model="nomic-embed-text", prompt=b)["embedding"]
                    col.add(
                        ids=[bid],
                        embeddings=[embedding],
                        documents=[b],
                        metadatas=[{"source": "mba_corpus", "url": url}],
                    )
                    existing_ids.add(bid)
                    bullets_added += 1

            except Exception as exc:
                logger.warning("Failed to scrape %s: %s", url, exc)
                urls_failed.append(url)

        return {
            "bullets_added": bullets_added,
            "urls_processed": urls_processed,
            "urls_failed": urls_failed,
        }

    def _rate_limit(self, domain: str) -> None:
        elapsed = time.time() - self._last_request[domain]
        if elapsed < _RATE_LIMIT_SECONDS:
            time.sleep(_RATE_LIMIT_SECONDS - elapsed)
        self._last_request[domain] = time.time()

    def _check_robots(self, url: str, requests: Any) -> bool:
        from urllib.parse import urljoin
        from urllib.robotparser import RobotFileParser

        parsed = urlparse(url)
        robots_url = urljoin(f"{parsed.scheme}://{parsed.netloc}", "/robots.txt")
        try:
            rp = RobotFileParser()
            rp.set_url(robots_url)
            resp = requests.get(robots_url, timeout=5, headers={"User-Agent": "ACOS-research-bot/1.0"})
            rp.parse(resp.text.splitlines())
            return rp.can_fetch("ACOS-research-bot", url)
        except Exception:
            return True  # ponytail: assume allowed if robots.txt unreachable
