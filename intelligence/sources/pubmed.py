"""PubMed 学术源适配器。"""

import hashlib
import logging
from datetime import datetime, timedelta
from typing import List

import requests

from intelligence.models import Article
from intelligence.sources.base import AcademicSource

logger = logging.getLogger(__name__)


class PubMedSource(AcademicSource):
    """PubMed E-utilities 适配器。"""

    name = "pubmed"
    _base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        if not query:
            query = ""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        date_range = f"{start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}"
        search_query = f"{query} AND {start_date.strftime('%Y/%m/%d')}[PDAT] : {end_date.strftime('%Y/%m/%d')}[PDAT]"

        try:
            search_url = f"{self._base_url}/esearch.fcgi"
            params = {
                "db": "pubmed",
                "term": search_query,
                "retmode": "json",
                "retmax": 50,
                "sort": "pub+date",
            }
            search_response = requests.get(search_url, params=params, timeout=30)
            search_response.raise_for_status()
            search_data = search_response.json()
            id_list = search_data.get("esearchresult", {}).get("idlist", [])
            if not id_list:
                return []

            summary_url = f"{self._base_url}/esummary.fcgi"
            summary_params = {
                "db": "pubmed",
                "id": ",".join(id_list),
                "retmode": "json",
            }
            summary_response = requests.get(summary_url, params=summary_params, timeout=30)
            summary_response.raise_for_status()
            summary_data = summary_response.json()
            result = summary_data.get("result", {})
        except Exception as exc:
            logger.warning("PubMed API 调用失败: %s", exc)
            return []

        articles: List[Article] = []
        for pmid in id_list:
            item = result.get(pmid, {})
            title = item.get("title", "").strip()
            if not title:
                continue
            authors = []
            for author in item.get("authors", []):
                name = author.get("name", "")
                if name:
                    authors.append(name)
            pub_date = ""
            date_parts = item.get("pubdate", "").split()
            if date_parts:
                try:
                    year = int(date_parts[0])
                    pub_date = f"{year}-01-01"
                except ValueError:
                    pub_date = item.get("pubdate", "")
            url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            doi = ""
            for article_id in item.get("articleids", []):
                if article_id.get("idtype") == "doi":
                    doi = article_id.get("value", "")
                    break

            article_id = self._article_id(title, url)
            articles.append(
                Article(
                    id=article_id,
                    title=title,
                    abstract="",
                    authors=authors,
                    url=url,
                    doi=doi,
                    published_date=pub_date,
                    source=self.name,
                    raw=dict(item),
                )
            )
        logger.info("PubMed 获取 %d 篇最近文章 (query=%s)", len(articles), query)
        return articles

    @staticmethod
    def _article_id(title: str, url: str) -> str:
        text = f"pubmed:{title}:{url}"
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]
