import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from jinja2 import Template

from agent.config import Config
from agent.llm import LLMClient
from agent.research_state import ResearchState

logger = logging.getLogger(__name__)


DEFAULT_TEMPLATE = """# {{ title }}

**研究主题**: {{ topic }}  
**生成时间**: {{ now }}  
**模型**: {{ model }}

---

{{ content }}

---

## 参考来源

{% for source in sources %}
[{{ source.index }}] [{{ source.title }}]({{ source.url }})  
{% endfor %}
"""


def generate_report(
    topic: str,
    state: ResearchState,
    config: Config,
    llm: LLMClient,
) -> str:
    logger.info("正在分析跨来源关联...")
    connections = llm.find_connections(
        topic=topic,
        findings=state.findings,
        entities=state.entities,
        language=config.research.language,
    )

    logger.info("正在生成报告正文...")
    report_body = llm.generate_report(
        topic=topic,
        findings=state.findings,
        entities=state.entities,
        connections=connections,
        sources=[{"title": s.title, "url": s.url} for s in state.sources],
        language=config.research.language,
    )

    data = {
        "title": config.report.title,
        "topic": topic,
        "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "model": config.llm.model,
        "content": report_body,
        "sources": state.sources,
    }

    template = Template(DEFAULT_TEMPLATE)
    return template.render(**data)


def save_report(report: str, output_path: str) -> str:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report, encoding="utf-8")
    logger.info("报告已保存至: %s", path)
    return str(path)
