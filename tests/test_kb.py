"""知识库模块单元测试。"""

import json
import tempfile
from pathlib import Path

import pytest

from kb import (
    KnowledgeStore,
    build_topic_graph,
    extract_timeline,
    parse_markdown_report,
    parse_research_state,
)
from kb.models import Report


def test_parse_research_state_basic():
    state = {
        "sources": [
            {"index": 1, "title": "Example", "url": "https://example.com", "snippet": ""}
        ],
        "summaries": [
            {
                "source_index": 1,
                "url": "https://example.com",
                "title": "Example",
                "summary": "summary",
                "key_findings": ["finding 1"],
                "entities": ["AI", "Machine Learning"],
                "open_questions": [],
                "relevance_score": 8,
            }
        ],
        "findings": ["finding 1"],
        "entities": ["AI", "Machine Learning"],
        "open_questions": [],
        "themes": ["Technology"],
        "connections": [],
        "contradictions": [],
        "gaps": [],
        "verification_results": [],
        "editor_feedback": [],
        "revisions": [],
    }

    report = parse_research_state(
        state=state,
        report_id="r1",
        title="Test Report",
        topic="AI",
        content="This is about AI in 2024.",
    )

    assert report.id == "r1"
    assert report.title == "Test Report"
    assert len(report.findings) == 1
    assert len(report.entities) == 2
    assert len(report.topics) == 1
    assert report.topics[0].name == "Technology"


def test_extract_timeline():
    text = "2023年，研究团队发布了第一个版本。2024年6月，系统增加了可视化功能。预计在2025年完成。"
    events = extract_timeline(text, report_id="r1", report_title="Test")

    assert len(events) >= 2
    assert any("2023" in e.date_text for e in events)
    assert any("2024" in e.date_text for e in events)

    # 检查排序
    dates = [e.date_iso for e in events if e.date_iso]
    assert dates == sorted(dates)


def test_build_topic_graph():
    report1 = Report(
        id="r1",
        title="R1",
        topic="T1",
        created_at="2024-01-01",
        entities=[{"id": "e1", "name": "AI", "report_ids": ["r1"], "count": 1}],
        content="",
    )
    report2 = Report(
        id="r2",
        title="R2",
        topic="T2",
        created_at="2024-01-02",
        entities=[
            {"id": "e1", "name": "AI", "report_ids": ["r2"], "count": 1},
            {"id": "e2", "name": "Quantum", "report_ids": ["r2"], "count": 1},
        ],
        content="",
    )

    graph = build_topic_graph([report1, report2])
    assert len(graph["nodes"]) == 2
    assert len(graph["links"]) == 1
    assert graph["links"][0]["source"] == "ai"
    assert graph["links"][0]["target"] == "quantum"


def test_knowledge_store_add_and_search():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = KnowledgeStore(data_dir=tmpdir)
        report = Report(
            id="r1",
            title="AI Report",
            topic="AI",
            created_at="2024-01-01",
            content="Artificial intelligence is transforming research in 2024.",
            entities=[{"id": "e1", "name": "AI", "report_ids": ["r1"], "count": 1}],
            findings=[{"text": "AI is important"}],
        )
        store.add_report(report)

        # 重新加载以验证持久化
        store2 = KnowledgeStore(data_dir=tmpdir)
        assert "r1" in store2.kb.reports
        assert store2.get_stats()["report_count"] == 1

        results = store2.search_reports("AI")
        assert len(results) == 1
        assert results[0]["report"]["id"] == "r1"


def test_parse_markdown_report(tmp_path):
    md = tmp_path / "test.md"
    md.write_text(
        "# 深度研究报告\n\n"
        "**研究主题**: 量子计算\n"
        "**生成时间**: 2024-06-20 10:00:00\n"
        "**模型**: gpt-4o-mini\n\n"
        "---\n\n"
        "量子计算在2024年取得了重要进展。\n\n"
        "## 参考来源\n\n"
        "[1] [Example](https://example.com)\n",
        encoding="utf-8",
    )

    report = parse_markdown_report(str(md))
    assert report.title == "深度研究报告"
    assert report.topic == "量子计算"
    assert len(report.events) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
