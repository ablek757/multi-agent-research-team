"""多模态输出格式器测试。"""

import tempfile
from pathlib import Path

from agent.config import Config
from agent.output import get_formatter, list_formats
from agent.research_state import ResearchState


def test_list_formats():
    formats = list_formats()
    assert "markdown" in formats
    assert "slides" in formats
    assert "html" in formats
    assert "dataset_brief" in formats
    assert "action_plan" in formats


def test_markdown_formatter():
    config = Config.load("config.yaml")
    state = ResearchState()
    state.report_body = "## 背景\n这是背景。\n\n## 发现\n- 发现一"
    state.add_source("示例", "https://example.com", "snippet")

    formatter = get_formatter("markdown", config)
    artifact = formatter.format("测试主题", state)
    assert artifact.format == "markdown"
    assert "测试主题" in artifact.content
    assert "发现一" in artifact.content


def test_html_formatter_creates_file():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config.load("config.yaml")
        config.report.output_dir = tmp
        state = ResearchState()
        state.report_body = "## 标题\n内容。"

        formatter = get_formatter("html", config)
        artifact = formatter.format("测试主题", state)
        assert artifact.file_path
        assert Path(artifact.file_path).exists()
        assert "<html" in artifact.content


def test_dataset_brief_formatter():
    with tempfile.TemporaryDirectory() as tmp:
        config = Config.load("config.yaml")
        config.report.output_dir = tmp
        state = ResearchState()
        state.add_source("示例", "https://example.com", "snippet")
        state.findings = ["finding 1", "finding 2 with 99% accuracy"]

        formatter = get_formatter("dataset_brief", config)
        artifact = formatter.format("测试主题", state)
        assert artifact.format == "dataset_brief"
        assert Path(artifact.file_path).exists()
        assert artifact.metadata["row_count"] >= 2
