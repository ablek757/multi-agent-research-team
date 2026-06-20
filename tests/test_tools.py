"""工具注册表测试。"""

import pytest

from agent.config import Config
from agent.tools import BaseTool, ToolRegistry, ToolResult, build_default_registry
from agent.tools.calculator_tool import CalculatorTool
from agent.tools.date_tool import DateTool
from agent.tools.fetch_tool import FetchTool
from agent.tools.kb_tool import KBQueryTool
from agent.tools.search_tool import SearchTool


class EchoTool(BaseTool):
    name = "echo"
    description = "echo"
    input_schema = {"type": "object", "properties": {"text": {"type": "string"}}}

    def run(self, text: str) -> ToolResult:
        return ToolResult(success=True, data={"echo": text})


def test_registry_register_and_call():
    registry = ToolRegistry()
    registry.register(EchoTool())
    assert "echo" in registry
    data = registry.call("echo", text="hello")
    assert data == {"echo": "hello"}


def test_default_registry_build():
    config = Config.load("config.yaml")
    registry = build_default_registry(config=config)
    tools = registry.list_tools()
    names = [t["name"] for t in tools]
    assert "web_search" in names
    assert "fetch_page" in names
    assert "kb_query" in names
    assert "calculator" in names
    assert "date" in names


def test_calculator():
    tool = CalculatorTool()
    result = tool.run("(2 + 3) * 4")
    assert result.success
    assert result.data["result"] == 20

    bad = tool.run("__import__('os').system('ls')")
    assert not bad.success


def test_date_now():
    tool = DateTool()
    result = tool.run(action="now")
    assert result.success
    assert "iso" in result.data


def test_kb_query_without_store():
    tool = KBQueryTool()
    result = tool.run(action="stats")
    assert not result.success
    assert "KB store not available" in result.error
