"""实时情报系统单元测试。"""

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from agent.config import Config
from intelligence.matcher import IntelligenceMatcher
from intelligence.models import Article, RelevanceScores
from intelligence.notifier import Notifier
from intelligence.service import IntelligenceService
from intelligence.sources.arxiv import ArxivSource
from intelligence.store import IntelligenceStore


def test_article_model():
    article = Article(
        id="test-id",
        title="Test Title",
        abstract="Test abstract",
        authors=["Alice"],
        url="https://example.com",
        doi="10.1234/test",
        published_date=datetime.now(timezone.utc).isoformat(),
        source="arxiv",
    )
    assert article.title == "Test Title"
    assert article.source == "arxiv"


def test_scores_threshold():
    scores = RelevanceScores(relevance=8, novelty=8, breakthrough=8)
    assert scores.above_threshold({"relevance": 7, "novelty": 7, "breakthrough": 7})
    scores2 = RelevanceScores(relevance=6, novelty=8, breakthrough=8)
    assert not scores2.above_threshold({"relevance": 7, "novelty": 7, "breakthrough": 7})


def test_store_add_and_list():
    with tempfile.TemporaryDirectory() as tmp:
        store = IntelligenceStore(data_dir=tmp)
        article = Article(
            id="a1",
            title="Title",
            abstract="Abstract",
            url="https://example.com",
            source="arxiv",
        )
        alert = AlertForTest(article, "topic")
        store.add_alert(alert)
        result = store.list_alerts(topic="topic")
        assert result["total"] == 1
        assert result["alerts"][0]["article"]["id"] == "a1"


def test_matcher_generate_queries():
    with tempfile.TemporaryDirectory() as tmp:
        store = IntelligenceStore(data_dir=tmp)
        llm = MagicMock()
        matcher = IntelligenceMatcher(llm=llm, store=store)
        queries = matcher.generate_queries(
            topic="quantum computing",
            entities=["IBM", "Google"],
            count=3,
        )
        assert len(queries) == 3
        assert "quantum computing" in queries


def test_notifier_console_channel():
    config = Config.load()
    config.intelligence.notify.channels = ["console"]
    notifier = Notifier(config)
    article = Article(id="a1", title="T", abstract="A", source="arxiv")
    alert = AlertForTest(article, "topic")
    notifier.notify_alerts([alert])


def test_intelligence_service_topics():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config.load()
        config.kb.data_dir = tmp
        # 空知识库应返回空主题
        service = IntelligenceService(config)
        assert service.get_monitor_topics() == {}


def AlertForTest(article, topic):
    from intelligence.models import Alert

    return Alert(
        id=f"{topic}:{article.id}",
        topic=topic,
        article=article,
        scores=RelevanceScores(relevance=8, novelty=8, breakthrough=8),
    )
