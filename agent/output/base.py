"""多模态输出格式器抽象基类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict

from agent.config import Config
from agent.research_state import ResearchState


@dataclass
class OutputArtifact:
    """输出产物。"""

    format: str
    content: str = ""
    file_path: str = ""
    mime_type: str = "text/plain"
    metadata: Dict[str, Any] = field(default_factory=dict)


class OutputFormatter(ABC):
    """输出格式器抽象基类。"""

    name: str = ""
    mime_type: str = "text/plain"
    extension: str = ""

    def __init__(self, config: Config, style_profile=None):
        self.config = config
        self.style_profile = style_profile

    @abstractmethod
    def format(self, topic: str, state: ResearchState) -> OutputArtifact:
        """将研究状态格式化为输出产物。"""
        raise NotImplementedError

    def _build_report_body(self, topic: str, state: ResearchState) -> str:
        """确保 state 中包含报告正文。"""
        if state.report_body:
            return state.report_body
        from agent.agents.writer import Writer

        writer = Writer(self.config.llm)
        body = writer.write(
            topic,
            state,
            self.config.research.language,
            style_profile=self.style_profile,
        )
        state.report_body = body
        return body
