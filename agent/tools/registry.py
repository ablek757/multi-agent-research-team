"""工具注册表：统一管理并分发所有可调用工具。"""

import logging
from typing import Any, Dict, List, Optional, Type

from agent.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表，支持注册、发现、按名称调用工具。"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """注册一个工具实例。"""
        if not tool.name:
            raise ValueError("Tool must have a name")
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def register_many(self, tools: List[BaseTool]) -> None:
        for tool in tools:
            self.register(tool)

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        """返回所有工具的模式描述，供 LLM function calling 使用。"""
        return [tool.get_schema() for tool in self._tools.values()]

    def call(self, name: str, **kwargs) -> Any:
        """按名称调用工具并返回结果数据。"""
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool not found: {name}")
        result = tool.run(**kwargs)
        if not result.success:
            raise RuntimeError(f"Tool {name} failed: {result.error}")
        return result.data

    def call_safe(self, name: str, **kwargs) -> Any:
        """安全调用，失败返回 None 并记录日志。"""
        try:
            return self.call(name, **kwargs)
        except Exception as exc:
            logger.warning("Tool call failed: %s", exc)
            return None

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# 全局注册表实例
_REGISTRY: Optional[ToolRegistry] = None


def get_global_registry() -> ToolRegistry:
    global _REGISTRY
    if _REGISTRY is None:
        _REGISTRY = ToolRegistry()
    return _REGISTRY


def build_default_registry(**deps) -> ToolRegistry:
    """构建默认工具注册表，注入 config/state/kb_store 等依赖。"""
    from agent.tools.calculator_tool import CalculatorTool
    from agent.tools.date_tool import DateTool
    from agent.tools.fetch_tool import FetchTool
    from agent.tools.kb_tool import KBQueryTool
    from agent.tools.search_tool import SearchTool

    registry = ToolRegistry()
    registry.register_many(
        [
            SearchTool(**deps),
            FetchTool(**deps),
            KBQueryTool(**deps),
            CalculatorTool(**deps),
            DateTool(**deps),
        ]
    )
    return registry
