import json
import logging
from datetime import datetime
from pathlib import Path

from jinja2 import Template

from agent.agents.writer import Writer
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


def _append_traceability_report(report_body: str, state: ResearchState) -> str:
    """若存在可信验证与溯源报告，则追加到正文末尾。"""
    if not state.traceability_report:
        return report_body
    if state.traceability_report.strip() in report_body:
        return report_body
    return report_body + "\n\n" + state.traceability_report


def generate_report(
    topic: str,
    state: ResearchState,
    config: Config,
    llm: LLMClient | None = None,
) -> str:
    """生成 Markdown 研究报告。

    如果研究团队已经生成报告正文，则直接包装；否则使用 Writer 生成。
    """
    if state.report_body:
        logger.info("使用研究团队已生成的报告正文...")
        report_body = state.report_body
    else:
        logger.info("研究团队尚未生成报告，使用 Writer 生成...")
        writer = Writer(config.llm)
        report_body = writer.write(topic, state, config.research.language)
        state.report_body = report_body

    report_body = _append_traceability_report(report_body, state)

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


def save_state(state: ResearchState, output_path: str) -> str:
    """保存 ResearchState 为 JSON，供知识库解析使用。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = state.to_dict()
    data["report_body"] = state.report_body
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("研究状态已保存至: %s", path)
    return str(path)
