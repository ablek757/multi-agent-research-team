"""情报系统数据模型。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class Article:
    """从学术源获取的一篇文章。"""

    id: str
    title: str
    abstract: str = ""
    authors: List[str] = field(default_factory=list)
    url: str = ""
    doi: str = ""
    published_date: Optional[str] = None
    source: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "url": self.url,
            "doi": self.doi,
            "published_date": self.published_date,
            "source": self.source,
        }


@dataclass
class RelevanceScores:
    """文章与监控主题的相关性与突破程度评分。"""

    relevance: int = 5
    novelty: int = 5
    breakthrough: int = 5
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "relevance": self.relevance,
            "novelty": self.novelty,
            "breakthrough": self.breakthrough,
            "reason": self.reason,
        }

    def above_threshold(self, thresholds: Dict[str, int]) -> bool:
        return (
            self.relevance >= thresholds.get("relevance", 7)
            and self.novelty >= thresholds.get("novelty", 7)
            and self.breakthrough >= thresholds.get("breakthrough", 7)
        )


@dataclass
class Alert:
    """匹配到的重要情报告警。"""

    id: str
    topic: str
    article: Article
    scores: RelevanceScores
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notified: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "article": self.article.to_dict(),
            "scores": self.scores.to_dict(),
            "created_at": self.created_at,
            "notified": self.notified,
        }


@dataclass
class Briefing:
    """针对某一主题生成的个性化研究简报。"""

    id: str
    topic: str
    title: str
    date: str
    content: str
    alerts: List[Alert] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    markdown_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "title": self.title,
            "date": self.date,
            "content": self.content,
            "alerts": [a.to_dict() for a in self.alerts],
            "created_at": self.created_at,
            "markdown_path": self.markdown_path,
        }
