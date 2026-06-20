"""arXiv 学术源适配器。"""

import hashlib
import logging
from typing import List

import feedparser

from intelligence.models import Article
from intelligence.sources.base import AcademicSource

logger = logging.getLogger(__name__)


class ArxivSource(AcademicSource):
    """arXiv API 适配器（使用 Atom feed）。"""

    name = "arxiv"
    _base_url = "http://export.arxiv.org/api/query"

    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        import urllib.parse

        if not query:
            query = "all"
        search_query = f"all:{query}"
        url = (
            f"{self._base_url}?search_query={urllib.parse.quote(search_query)}"
            f"&sortBy=submittedDate&sortOrder=descending&max_results=50"
        )
        try:
            feed = feedparser.parse(url)
        except Exception as exc:
            logger.warning("arXiv feed 解析失败: %s", exc)
            return []

        articles: List[Article] = []
        cutoff = self._cutoff_date(days)
        for entry in feed.entries:
            published = entry.get("published", "")
            try:
                dt = self._parse_date(published)
            except Exception:
                continue
            if dt < cutoff:
                continue

            title = entry.get("title", "").replace("\n", " ").strip()
            abstract = entry.get("summary", "").replace("\n", " ").strip()
            url = ""
            for link in entry.get("links", []):
                if link.get("type") == "text/html":
                    url = link.get("href", "")
                    break
            if not url:
                url = entry.get("link", "")
            authors = [a.get("name", "") for a in entry.get("authors", [])]
            doi = ""
            for link in entry.get("links", []):
                if link.get("title") == "doi":
                    doi = link.get("href", "").replace("https://doi.org/", "")
                    break

            article_id = self._article_id(title, url)
            articles.append(
                Article(
                    id=article_id,
                    title=title,
                    abstract=abstract,
                    authors=authors,
                    url=url,
                    doi=doi,
                    published_date=published,
                    source=self.name,
                    raw=dict(entry),
                )
            )
        logger.info("arXiv 获取 %d 篇最近文章 (query=%s)", len(articles), query)
        return articles

    @staticmethod
    def _parse_date(date_str: str):
        from datetime import datetime

        return datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        text = f"arxiv:{title}:{url}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
