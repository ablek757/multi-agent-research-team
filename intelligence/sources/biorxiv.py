"""bioRxiv 学术源适配器。"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List

import requests

from intelligence.models import Article
from intelligence.sources.base import AcademicSource

logger = logging.getLogger(__name__)


class BiorxivSource(AcademicSource):
    """bioRxiv API 适配器。"""

    name = "biorxiv"
    _base_url = "https://api.biorxiv.org/details/biorxiv"

    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        # API 限制一次最多 30 天或 100 条，days 较小时按区间查询
        interval = f"{start_date.strftime('%Y-%m-%d')}/{end_date.strftime('%Y-%m-%d')}"
        url = f"{self._base_url}/{interval}"
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("bioRxiv API 调用失败: %s", exc)
            return []

        articles: List[Article] = []
        cutoff = self._cutoff_date(days)
        for item in data.get("collection", []):
            published = item.get("date", "")
            try:
                dt = datetime.strptime(published, "%Y-%m-%d")
            except Exception:
                continue
            if dt < cutoff:
                continue

            title = item.get("title", "").strip()
            if not title:
                continue
            authors_raw = item.get("authors", "")
            authors = [a.strip() for a in authors_raw.split(";") if a.strip()]
            doi = item.get("doi", "")
            url = item.get("url", "")
            if not url and doi:
                url = f"https://doi.org/{doi}"

            # 如果提供了查询词，按标题/摘要做简单过滤
            abstract = item.get("abstract", "")
            if query and query.lower() not in title.lower() and query.lower() not in abstract.lower():
                continue

            article_id = self._article_id(title, url or doi)
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
                    raw=dict(item),
                )
            )
        logger.info("bioRxiv 获取 %d 篇最近文章 (query=%s)", len(articles), query)
        return articles

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        text = f"biorxiv:{title}:{url}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
