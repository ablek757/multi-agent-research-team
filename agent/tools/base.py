"""通用工具抽象基类。"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """工具执行结果。"""

    success: bool = True
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """工具抽象基类。

    所有可被认知控制器或 Agent 调用的能力都应实现此接口。
    """

    name: str = ""
    description: str = ""
    input_schema: Dict[str, Any] = {}

    def __init__(self, **deps):
        """通过依赖注入接收 config、state、kb_store、llm 等上下文。"""
        self.deps = deps

    @abstractmethod
    def run(self, **kwargs) -> ToolResult:
        """执行工具并返回结果。"""
        raise NotImplementedError

    def get_schema(self) -> Dict[str, Any]:
        """返回给 LLM 的 JSON Schema 描述。"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.input_schema,
        }
