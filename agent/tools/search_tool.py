"""搜索工具：将 SearchEngine 封装为可调用工具。"""

from typing import Any, Dict, List

from agent.config import Config
from agent.search import SearchEngine
from agent.tools.base import BaseTool, ToolResult


class SearchTool(BaseTool):
    """使用配置的后端（默认 DuckDuckGo）执行网页搜索。"""

    name = "web_search"
    description = "执行网页搜索，返回标题、URL 和摘要列表。"
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索查询词",
            },
            "num_results": {
                "type": "integer",
                "description": "期望返回结果数（可选）",
                "default": 5,
            },
        },
        "required": ["query"],
    }

    def __init__(self, **deps):
        super().__init__(**deps)
        config: Config = deps.get("config")
        if config is None:
            raise ValueError("SearchTool requires 'config' dependency")
        self.engine = SearchEngine(config.search)

    def run(self, query: str, num_results: int = 5) -> ToolResult:
        try:
            results = self.engine.search(query, num_results=num_results)
            data: List[Dict[str, Any]] = [
                {
                    "title": r.title,
                    "url": r.url,
                    "snippet": r.snippet,
                }
                for r in results
            ]
            return ToolResult(success=True, data=data, metadata={"count": len(data)})
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
