"""解析 Markdown 报告与 ResearchState JSON。"""

import hashlib
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.models import Entity, Event, Finding, Report, Source, Topic
from kb.timeline import extract_timeline


def _generate_id(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def _normalize_name(name: str) -> str:
    return " ".join(name.lower().split())


def parse_research_state(
    state: Dict[str, Any],
    report_id: Optional[str] = None,
    title: str = "深度研究报告",
    topic: str = "",
    created_at: str = "",
    model: str = "",
    content: str = "",
    markdown_path: Optional[str] = None,
    state_path: Optional[str] = None,
) -> Report:
    """从 ResearchState dict 构建 Report 对象。"""
    report_id = report_id or str(uuid.uuid4())
    created_at = created_at or datetime.now().isoformat()

    sources = [
        Source(
            index=s.get("index", idx + 1),
            title=s.get("title", ""),
            url=s.get("url", ""),
            snippet=s.get("snippet", ""),
        )
        for idx, s in enumerate(state.get("sources", []))
    ]

    findings: List[Finding] = []
    for summary in state.get("summaries", []):
        url = summary.get("url", "")
        source_index = next((s.index for s in sources if s.url == url), None)
        for text in summary.get("key_findings", []):
            findings.append(
                Finding(
                    text=text,
                    source_index=source_index,
                    source_url=url,
                )
            )

    for text in state.get("findings", []):
        if not any(f.text == text for f in findings):
            findings.append(Finding(text=text))

    entities: List[Entity] = []
    seen_entities: set = set()
    for name in state.get("entities", []):
        key = _normalize_name(name)
        if key and key not in seen_entities:
            seen_entities.add(key)
            entities.append(
                Entity(
                    id=_generate_id(key),
                    name=name.strip(),
                    report_ids=[report_id],
                )
            )

    topics: List[Topic] = []
    seen_topics: set = set()
    for name in state.get("themes", []):
        key = _normalize_name(name)
        if key and key not in seen_topics:
            seen_topics.add(key)
            topics.append(
                Topic(
                    id=_generate_id(key),
                    name=name.strip(),
                    report_ids=[report_id],
                )
            )

    events = extract_timeline(content, report_id=report_id, report_title=title)

    return Report(
        id=report_id,
        title=title,
        topic=topic,
        created_at=created_at,
        model=model,
        content=content,
        sources=sources,
        findings=findings,
        entities=entities,
        topics=topics,
        events=events,
        markdown_path=markdown_path,
        state_path=state_path,
    )


def parse_markdown_report(
    markdown_path: str,
    state_path: Optional[str] = None,
    report_id: Optional[str] = None,
) -> Report:
    """从 Markdown 文件与可选的 state JSON 解析报告。"""
    md_path = Path(markdown_path)
    content = md_path.read_text(encoding="utf-8")

    title = "深度研究报告"
    topic = ""
    created_at = ""
    model = ""

    title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

    topic_match = re.search(r"\*\*研究主题\*\*[:：]\s*(.+)", content)
    if topic_match:
        topic = topic_match.group(1).strip()

    time_match = re.search(r"\*\*生成时间\*\*[:：]\s*(\d{4}-\d{2}-\d{2}[\s\d:\-]*)", content)
    if time_match:
        created_at = time_match.group(1).strip()

    model_match = re.search(r"\*\*模型\*\*[:：]\s*(.+)", content)
    if model_match:
        model = model_match.group(1).strip()

    state: Dict[str, Any] = {}
    if state_path:
        state_file = Path(state_path)
        if state_file.exists():
            import json

            state = json.loads(state_file.read_text(encoding="utf-8"))

    report = parse_research_state(
        state=state,
        report_id=report_id,
        title=title,
        topic=topic,
        created_at=created_at,
        model=model,
        content=content,
        markdown_path=str(md_path.resolve()),
        state_path=str(Path(state_path).resolve()) if state_path else None,
    )
    return report
