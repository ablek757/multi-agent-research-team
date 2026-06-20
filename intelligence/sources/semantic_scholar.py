"""Semantic Scholar 学术源适配器。"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List

import requests

from intelligence.models import Article
from intelligence.sources.base import AcademicSource

logger = logging.getLogger(__name__)


class SemanticScholarSource(AcademicSource):
    """Semantic Scholar API 适配器。

    无需 API Key 即可使用基础搜索，但调用频率受限。
    可通过环境变量 S2_API_KEY 设置 Key 提高限额。
    """

    name = "semantic_scholar"
    _base_url = "https://api.semanticscholar.org/graph/v1"

    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        if not query:
            query = "machine learning"
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        # Semantic Scholar 支持按 publicationDate 过滤
        url = f"{self._base_url}/paper/search"
        params = {
            "query": query,
            "fields": "title,abstract,authors,year,publicationDate,externalIds,url",
            "limit": 50,
            "publicationDateOrYear": f"{start_date.strftime('%Y-%m-%d')}:{end_date.strftime('%Y-%m-%d')}",
        }
        headers = {}
        api_key = __import__("os").getenv("S2_API_KEY")
        if api_key:
            headers["x-api-key"] = api_key

        try:
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("Semantic Scholar API 调用失败: %s", exc)
            return []

        articles: List[Article] = []
        cutoff = self._cutoff_date(days)
        for item in data.get("data", []):
            pub_date = item.get("publicationDate") or f"{item.get('year')}-01-01"
            try:
                dt = datetime.fromisoformat(pub_date)
            except Exception:
                continue
            if dt < cutoff:
                continue

            title = item.get("title", "").strip()
            if not title:
                continue
            authors = []
            for author in item.get("authors", [])[:10]:
                name = author.get("name", "")
                if name:
                    authors.append(name)
            external_ids = item.get("externalIds", {}) or {}
            doi = external_ids.get("DOI", "")
            url = item.get("url", "")
            if not url and doi:
                url = f"https://doi.org/{doi}"

            article_id = self._article_id(title, url or doi)
            articles.append(
                Article(
                    id=article_id,
                    title=title,
                    abstract=item.get("abstract", ""),
                    authors=authors,
                    url=url,
                    doi=doi,
                    published_date=pub_date,
                    source=self.name,
                    raw=dict(item),
                )
            )
        logger.info("Semantic Scholar 获取 %d 篇最近文章 (query=%s)", len(articles), query)
        return articles

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        text = f"s2:{title}:{url}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
