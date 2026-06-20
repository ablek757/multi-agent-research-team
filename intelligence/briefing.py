"""个性化研究简报生成。"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
from typing import List

from agent.config import Config
from agent.llm import LLMClient
from intelligence.models import Alert, Briefing
from intelligence.store import IntelligenceStore

logger = logging.getLogger(__name__)


class BriefingGenerator:
    """基于告警生成个性化研究简报。"""

    def __init__(
        self,
        llm: LLMClient,
        store: IntelligenceStore,
        config: Config,
    ):
        self.llm = llm
        self.store = store
        self.config = config
        self.output_dir = Path(config.report.output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate(self, topic: str, alerts: List[Alert]) -> Briefing:
        """为指定主题生成简报。"""
        date_str = datetime.now().strftime("%Y-%m-%d")
        title = f"{topic} 实时情报简报 - {date_str}"
        content = self._write_briefing(topic, alerts, date_str)

        safe_topic = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic)[:40]
        filename = f"{safe_topic}_briefing_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        markdown_path = self.output_dir / filename
        markdown_path.write_text(content, encoding="utf-8")

        briefing_id = hashlib.md5(f"{topic}:{date_str}".encode("utf-8")).hexdigest()[:16]
        briefing = Briefing(
            id=briefing_id,
            topic=topic,
            title=title,
            date=date_str,
            content=content,
            alerts=alerts,
            markdown_path=str(markdown_path.resolve()),
        )
        self.store.add_briefing(briefing)
        logger.info("已生成简报: %s", title)
        return briefing

    def _write_briefing(self, topic: str, alerts: List[Alert], date_str: str) -> str:
        language = self.config.research.language
        lang_hint = "用中文撰写" if language == "zh" else "Write in English"

        sources_text = "\n".join(
            f"{idx}. [{a.article.title}]({a.article.url}) "
            f"(来源: {a.article.source}, 相关性: {a.scores.relevance}, "
            f"新颖性: {a.scores.novelty}, 突破性: {a.scores.breakthrough})\n"
            f"   摘要: {a.article.abstract[:500]}"
            for idx, a in enumerate(alerts, 1)
        )

        system = (
            "You are a senior research intelligence writer. Given a set of recent "
            "academic alerts, write a personalized, structured Markdown briefing. "
            "Highlight breakthroughs, connect them to the user's topic, and suggest "
            "next steps. Cite papers using [n] notation."
        )
        user = (
            f"主题: {topic}\n"
            f"日期: {date_str}\n\n"
            f"告警论文:\n{sources_text}\n\n"
            "请生成包含以下结构的 Markdown 简报:\n"
            "1. 执行摘要\n"
            "2. 核心突破\n"
            "3. 关键论文与发现\n"
            "4. 与知识库主题的关联\n"
            "5. 研究启示与后续建议\n\n"
            f"{lang_hint}"
        )
        try:
            return self.llm._chat(system, user)
        except Exception as exc:
            logger.warning("LLM 简报生成失败，使用模板: %s", exc)
            return self._fallback_briefing(topic, alerts, date_str)

    def _fallback_briefing(self, topic: str, alerts: List[Alert], date_str: str) -> str:
        lines = [
            f"# {topic} 实时情报简报 - {date_str}",
            "",
            "## 执行摘要",
            f"今日共发现 {len(alerts)} 条与「{topic}」相关的重要情报。",
            "",
            "## 关键论文",
        ]
        for idx, alert in enumerate(alerts, 1):
            lines.append(
                f"{idx}. [{alert.article.title}]({alert.article.url}) "
                f"(来源: {alert.article.source})"
            )
            lines.append(f"   - 相关性: {alert.scores.relevance}/10，新颖性: {alert.scores.novelty}/10，突破性: {alert.scores.breakthrough}/10")
            lines.append(f"   - {alert.article.abstract[:300]}")
        lines.extend(["", "## 研究启示", "建议持续关注上述方向的后续进展。"])
        return "\n".join(lines)
