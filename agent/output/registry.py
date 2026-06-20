"""输出格式器注册表。"""

from typing import Dict, Type

from agent.config import Config
from agent.output.action_plan import ActionPlanFormatter
from agent.output.base import OutputFormatter
from agent.output.dataset_brief import DatasetBriefFormatter
from agent.output.html import HTMLFormatter
from agent.output.markdown import MarkdownFormatter
from agent.output.slides import SlidesFormatter

FORMATTER_REGISTRY: Dict[str, Type[OutputFormatter]] = {
    "markdown": MarkdownFormatter,
    "slides": SlidesFormatter,
    "html": HTMLFormatter,
    "dataset_brief": DatasetBriefFormatter,
    "action_plan": ActionPlanFormatter,
}


def get_formatter(name: str, config: Config, style_profile=None) -> OutputFormatter:
    """按名称获取格式器实例。"""
    if name not in FORMATTER_REGISTRY:
        raise ValueError(f"Unknown output format: {name}. Available: {list(FORMATTER_REGISTRY.keys())}")
    return FORMATTER_REGISTRY[name](config, style_profile=style_profile)


def list_formats() -> list:
    return list(FORMATTER_REGISTRY.keys())
