"""HTML 演示格式器：生成单页 Reveal.js 风格演示。"""

import re
from datetime import datetime
from pathlib import Path
from typing import List

from agent.config import Config
from agent.output.base import OutputArtifact, OutputFormatter
from agent.research_state import ResearchState

HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>{{ title }}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background: #f5f5f5; }
        .reveal { max-width: 960px; margin: 0 auto; padding: 20px; }
        .slides section { background: white; border-radius: 12px; padding: 60px; margin-bottom: 40px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); min-height: 60vh; }
        h1 { font-size: 2.6em; color: #1a1a1a; margin-bottom: 0.2em; }
        h2 { font-size: 2em; color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 0.3em; }
        p, li { font-size: 1.2em; line-height: 1.8; color: #333; }
        ul { padding-left: 1.5em; }
        .subtitle { color: #666; font-size: 1.3em; }
        .meta { color: #999; font-size: 0.9em; margin-top: 40px; }
        .source { font-size: 0.95em; color: #555; }
        a { color: #3498db; }
    </style>
</head>
<body>
<div class="reveal">
    <div class="slides">
        <section>
            <h1>{{ title }}</h1>
            <p class="subtitle">{{ topic }}</p>
            <p class="meta">生成时间：{{ now }} | 模型：{{ model }}</p>
        </section>
        {{ slides }}
        <section>
            <h2>参考来源</h2>
            <ul>
            {% for source in sources %}
                <li class="source">[{{ source.index }}] <a href="{{ source.url }}">{{ source.title }}</a></li>
            {% endfor %}
            </ul>
        </section>
    </div>
</div>
</body>
</html>
"""


class HTMLFormatter(OutputFormatter):
    """生成单页 HTML 演示文档。"""

    name = "html"
    mime_type = "text/html"
    extension = ".html"

    def __init__(self, config: Config, style_profile=None):
        super().__init__(config, style_profile=style_profile)
        self.theme = config.output.html_theme

    def format(self, topic: str, state: ResearchState) -> OutputArtifact:
        report_body = self._build_report_body(topic, state)
        sections = self._split_sections(report_body)

        slides_html = "\n".join(
            f"<section>\n<h2>{self._escape(heading)}</h2>\n<ul>\n"
            + "\n".join(f"<li>{self._escape(b)}</li>" for b in bullets[:10])
            + "\n</ul>\n</section>"
            for heading, bullets in sections
        )

        from jinja2 import Template

        template = Template(HTML_TEMPLATE)
        html_content = template.render(
            title=self.config.report.title,
            topic=topic,
            now=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            model=self.config.llm.model,
            slides=slides_html,
            sources=state.sources,
        )

        file_path = str(Path(self.config.report.output_dir) / f"{self._safe_name(topic)}.html")
        Path(self.config.report.output_dir).mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(html_content, encoding="utf-8")

        return OutputArtifact(
            format=self.name,
            content=html_content,
            file_path=file_path,
            mime_type=self.mime_type,
            metadata={"slide_count": len(sections) + 2, "source_count": len(state.sources)},
        )

    def _split_sections(self, text: str) -> List[tuple]:
        sections = []
        current_heading = "要点"
        current_bullets: List[str] = []

        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("## "):
                if current_bullets:
                    sections.append((current_heading, current_bullets))
                current_heading = line.lstrip("# ").strip()
                current_bullets = []
            elif line.startswith("- ") or line.startswith("* "):
                current_bullets.append(line.lstrip("- *").strip())
            elif line and not line.startswith("#"):
                sentences = re.split(r"(?<=[。！？.!?])\s+", line)
                current_bullets.extend(sentences)

        if current_bullets:
            sections.append((current_heading, current_bullets))

        if not sections:
            sections.append(("研究摘要", [text[:500]]))
        return sections

    def _escape(self, text: str) -> str:
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _safe_name(self, topic: str) -> str:
        return re.sub(r'[\\/:*?"<>|]+', "_", topic)[:50]
