"""情报服务主类。"""

import logging
from typing import Callable, Dict, List, Optional

from agent.config import Config
from agent.llm import LLMClient
from intelligence.briefing import BriefingGenerator
from intelligence.matcher import IntelligenceMatcher
from intelligence.models import Alert, Article, Briefing
from intelligence.notifier import Notifier
from intelligence.sources import SOURCE_REGISTRY
from intelligence.sources.base import AcademicSource
from intelligence.store import IntelligenceStore
from kb import KnowledgeStore

logger = logging.getLogger(__name__)


class IntelligenceService:
    """实时研究情报服务。"""

    def __init__(
        self,
        config: Config,
        progress_callback: Optional[Callable[[str], None]] = None,
        kb_store: Optional[KnowledgeStore] = None,
        intelligence_store: Optional[IntelligenceStore] = None,
    ):
        self.config = config
        self.progress_callback = progress_callback or (lambda msg: None)
        self.llm = LLMClient(config.llm)
        self.store = intelligence_store or IntelligenceStore(data_dir=config.kb.data_dir)
        self.kb = kb_store or KnowledgeStore(data_dir=config.kb.data_dir)
        self.matcher = IntelligenceMatcher(
            llm=self.llm,
            store=self.store,
            thresholds=config.intelligence.thresholds.__dict__,
        )
        self.briefing_generator = BriefingGenerator(
            llm=self.llm,
            store=self.store,
            config=config,
        )
        self.notifier = Notifier(config)
        self.sources: Dict[str, AcademicSource] = {}
        self._init_sources()

    def _init_sources(self):
        for name in self.config.intelligence.sources:
            cls = SOURCE_REGISTRY.get(name)
            if cls:
                self.sources[name] = cls()
                logger.info("已加载学术源: %s", name)
            else:
                logger.warning("未知学术源: %s", name)

    def _progress(self, message: str):
        logger.info(message)
        self.progress_callback(message)

    def get_monitor_topics(self) -> Dict[str, Dict[str, List[str]]]:
        """从知识库提取监控主题与相关实体。"""
        topics: Dict[str, Dict[str, List[str]]] = {}
        for report in self.kb.kb.reports.values():
            topic = report.topic or report.title
            if not topic:
                continue
            if topic not in topics:
                topics[topic] = {"entities": [], "report_ids": []}
            topics[topic]["report_ids"].append(report.id)
            for entity in report.entities:
                if entity.name not in topics[topic]["entities"]:
                    topics[topic]["entities"].append(entity.name)
        return topics

    def scan_topic(self, topic: str, entities: List[str]) -> List[Alert]:
        """扫描单个主题并返回告警。"""
        self._progress(f"开始扫描主题: {topic}")
        queries = self.matcher.generate_queries(topic, entities)
        all_articles: List[Article] = []

        for source_name, source in self.sources.items():
            for query in queries:
                try:
                    articles = source.fetch_recent(
                        days=self.config.intelligence.lookback_days,
                        query=query,
                    )
                    all_articles.extend(articles)
                    self._progress(
                        f"源 {source_name} / 查询 '{query}' 获取 {len(articles)} 篇文章"
                    )
                except Exception as exc:
                    logger.warning("扫描源 %s 失败: %s", source_name, exc)

        all_articles = self.matcher.deduplicate_articles(all_articles)
        self._progress(f"去重后共 {len(all_articles)} 篇文章")

        # 关键词预过滤
        filtered = self.matcher.filter_by_keywords(all_articles, topic, entities)
        self._progress(f"关键词过滤后剩余 {len(filtered)} 篇文章")

        alerts: List[Alert] = []
        for article in filtered:
            try:
                alert = self.matcher.evaluate(article, topic, entities)
                if alert:
                    alerts.append(alert)
            except Exception as exc:
                logger.warning("评估文章失败: %s", exc)

        self._progress(f"主题 '{topic}' 生成 {len(alerts)} 条告警")
        return alerts

    def run_scan(self, topics: Optional[List[str]] = None) -> Dict[str, List[Alert]]:
        """执行一次完整扫描。"""
        if not self.config.intelligence.enabled:
            self._progress("情报系统已禁用，跳过扫描")
            return {}

        monitor_topics = self.get_monitor_topics()
        if topics:
            monitor_topics = {k: v for k, v in monitor_topics.items() if k in topics}

        if not monitor_topics:
            self._progress("知识库为空或未指定主题，无法扫描")
            return {}

        self._progress(f"发现 {len(monitor_topics)} 个监控主题")
        all_alerts: Dict[str, List[Alert]] = {}
        for topic, meta in monitor_topics.items():
            alerts = self.scan_topic(topic, meta["entities"])
            if alerts:
                all_alerts[topic] = alerts

        # 推送未通知的告警
        new_alerts = [
            a for alerts in all_alerts.values() for a in alerts if not a.notified
        ]
        if new_alerts:
            self.notifier.notify_alerts(new_alerts)
            self.store.mark_alerts_notified([a.id for a in new_alerts])

        # 为每个有告警的主题生成简报
        briefings = []
        for topic, alerts in all_alerts.items():
            briefing = self.briefing_generator.generate(topic, alerts)
            briefings.append(briefing)

        if briefings:
            for briefing in briefings:
                self.notifier.notify_briefing(briefing)
                self._ingest_briefing_to_kb(briefing)

        self._progress(
            f"扫描完成: {sum(len(v) for v in all_alerts.values())} 条告警, "
            f"{len(briefings)} 份简报"
        )
        return all_alerts

    def _ingest_briefing_to_kb(self, briefing: Briefing):
        """将简报导入知识库，便于前端检索。"""
        try:
            from kb.parser import parse_markdown_report

            report = parse_markdown_report(
                markdown_path=briefing.markdown_path,
                report_id=briefing.id,
            )
            report.topic = briefing.topic
            report.title = briefing.title
            self.kb.add_report(report)
            self._progress(f"简报已导入知识库: {report.id}")
        except Exception as exc:
            logger.warning("简报导入知识库失败: %s", exc)

    def list_alerts(self, **kwargs):
        return self.store.list_alerts(**kwargs)

    def list_briefings(self, **kwargs):
        return self.store.list_briefings(**kwargs)
