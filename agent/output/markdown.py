"""Markdown 报告格式器。"""

from datetime import datetime
from pathlib import Path

from jinja2 import Template

from agent.config import Config
from agent.output.base import OutputArtifact, OutputFormatter
from agent.research_state import ResearchState

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


class MarkdownFormatter(OutputFormatter):
    """生成 Markdown 研究报告。"""

    name = "markdown"
    mime_type = "text/markdown"
    extension = ".md"

    def format(self, topic: str, state: ResearchState) -> OutputArtifact:
        report_body = self._build_report_body(topic, state)
        if state.traceability_report and state.traceability_report.strip() not in report_body:
            report_body = report_body + "\n\n" + state.traceability_report
        data = {
            "title": self.config.report.title,
            "topic": topic,
            "now": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "model": self.config.llm.model,
            "content": report_body,
            "sources": state.sources,
        }
        template = Template(DEFAULT_TEMPLATE)
        content = template.render(**data)
        return OutputArtifact(
            format=self.name,
            content=content,
            mime_type=self.mime_type,
            metadata={"source_count": len(state.sources)},
        )
