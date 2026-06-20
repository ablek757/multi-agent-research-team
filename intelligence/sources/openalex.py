"""OpenAlex 学术源适配器。"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List

import requests

from intelligence.models import Article
from intelligence.sources.base import AcademicSource

logger = logging.getLogger(__name__)


class OpenAlexSource(AcademicSource):
    """OpenAlex API 适配器。"""

    name = "openalex"
    _base_url = "https://api.openalex.org/works"

    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        if not query:
            query = "machine learning"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        params = {
            "search": query,
            "filter": f"from_publication_date:{start_date.strftime('%Y-%m-%d')},to_publication_date:{end_date.strftime('%Y-%m-%d')}",
            "sort": "publication_date:desc",
            "per-page": 50,
            "mailto": "user@example.com",
        }
        headers = {"User-Agent": "ResearchIntelligenceBot/1.0 (mailto:user@example.com)"}

        try:
            response = requests.get(self._base_url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("OpenAlex API 调用失败: %s", exc)
            return []

        articles: List[Article] = []
        cutoff = self._cutoff_date(days)
        for item in data.get("results", []):
            pub_date = item.get("publication_date", "")
            try:
                dt = datetime.fromisoformat(pub_date)
            except Exception:
                continue
            if dt < cutoff:
                continue

            title = item.get("display_name", "").strip()
            if not title:
                continue
            authors = []
            for authorship in item.get("authorships", [])[:10]:
                author = authorship.get("author", {})
                name = author.get("display_name", "")
                if name:
                    authors.append(name)
            doi = item.get("doi", "")
            url = item.get("primary_location", {}).get("landing_page_url", "")
            if not url and doi:
                url = doi

            article_id = self._article_id(title, url or doi)
            articles.append(
                Article(
                    id=article_id,
                    title=title,
                    abstract=item.get("abstract", "") or "",
                    authors=authors,
                    url=url,
                    doi=doi.replace("https://doi.org/", "") if doi else "",
                    published_date=pub_date,
                    source=self.name,
                    raw=dict(item),
                )
            )
        logger.info("OpenAlex 获取 %d 篇最近文章 (query=%s)", len(articles), query)
        return articles

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        text = f"openalex:{title}:{url}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
