"""情报匹配与评分。"""

import json
import logging
from typing import Dict, List, Optional, Tuple

from agent.llm import LLMClient
from intelligence.models import Alert, Article, RelevanceScores
from intelligence.store import IntelligenceStore

logger = logging.getLogger(__name__)


class IntelligenceMatcher:
    """将学术文章与知识库主题匹配并评分。"""

    def __init__(
        self,
        llm: LLMClient,
        store: IntelligenceStore,
        thresholds: Optional[Dict[str, int]] = None,
    ):
        self.llm = llm
        self.store = store
        self.thresholds = thresholds or {
            "relevance": 7,
            "novelty": 7,
            "breakthrough": 7,
        }

    def generate_queries(self, topic: str, entities: List[str], count: int = 3) -> List[str]:
        """基于主题与实体生成学术源查询。"""
        base = topic
        queries = [base]
        if entities:
            # 取前 5 个核心实体，生成组合查询
            top_entities = entities[:5]
            for entity in top_entities:
                q = f"{base} {entity}"
                if q not in queries:
                    queries.append(q)
        return queries[:count]

    def evaluate(
        self,
        article: Article,
        topic: str,
        context_entities: List[str],
    ) -> Optional[Alert]:
        """评估单篇文章，满足阈值则返回 Alert。"""
        if self.store.alert_exists(article.id, topic):
            return None

        scores = self._score_article(article, topic, context_entities)
        if not scores.above_threshold(self.thresholds):
            return None

        alert_id = f"{topic}:{article.id}"
        alert = Alert(
            id=alert_id,
            topic=topic,
            article=article,
            scores=scores,
        )
        self.store.add_alert(alert)
        return alert

    def _score_article(
        self,
        article: Article,
        topic: str,
        context_entities: List[str],
    ) -> RelevanceScores:
        system = (
            "You are an expert research intelligence analyst. Evaluate how much a "
            "recent academic article matches a user's research topic. "
            "Return ONLY valid JSON with keys: relevance (1-10), novelty (1-10), "
            "breakthrough (1-10), reason (short explanation in Chinese)."
        )
        entities_text = ", ".join(context_entities[:20]) if context_entities else "N/A"
        user = (
            f"User research topic: {topic}\n"
            f"Related entities in knowledge base: {entities_text}\n\n"
            f"Article title: {article.title}\n"
            f"Article abstract: {article.abstract[:2000]}\n"
            f"Source: {article.source}\n\n"
            "Evaluate relevance, novelty, and breakthrough potential."
        )
        try:
            content = self.llm._chat(system, user, json_mode=True)
            data = json.loads(content)
            return RelevanceScores(
                relevance=_clamp(int(data.get("relevance", 5))),
                novelty=_clamp(int(data.get("novelty", 5))),
                breakthrough=_clamp(int(data.get("breakthrough", 5))),
                reason=data.get("reason", ""),
            )
        except Exception as exc:
            logger.warning("LLM 评分失败: %s", exc)
            return RelevanceScores(relevance=5, novelty=5, breakthrough=5, reason="")

    def deduplicate_articles(self, articles: List[Article]) -> List[Article]:
        """按 id 去重，保留最先出现的文章。"""
        seen: set = set()
        result: List[Article] = []
        for article in articles:
            if article.id not in seen:
                seen.add(article.id)
                result.append(article)
        return result

    def filter_by_keywords(
        self,
        articles: List[Article],
        topic: str,
        entities: List[str],
    ) -> List[Article]:
        """基于关键词预过滤，减少 LLM 调用。"""
        keywords = [topic.lower()]
        keywords.extend(e.lower() for e in entities if e)
        filtered = []
        for article in articles:
            text = f"{article.title} {article.abstract}".lower()
            if any(k in text for k in keywords):
                filtered.append(article)
        return filtered


def _clamp(value: int, low: int = 1, high: int = 10) -> int:
    return max(low, min(high, value))
