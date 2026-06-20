"""网页抓取工具：将 fetch_page 封装为可调用工具。"""

from typing import Any, Dict

from agent.fetcher import fetch_page
from agent.tools.base import BaseTool, ToolResult


class FetchTool(BaseTool):
    """抓取指定 URL 并提取正文内容。"""

    name = "fetch_page"
    description = "抓取网页 URL，返回标题和正文内容。"
    input_schema = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "要抓取的网页 URL",
            },
            "max_length": {
                "type": "integer",
                "description": "最大返回字符数",
                "default": 12000,
            },
        },
        "required": ["url"],
    }

    def run(self, url: str, max_length: int = 12000) -> ToolResult:
        try:
            page = fetch_page(url, max_length=max_length)
            data: Dict[str, Any] = {
                "url": page.url,
                "title": page.title,
                "content": page.content,
                "status": page.status,
            }
            metadata = {"has_error": page.error is not None}
            if page.error:
                metadata["error"] = page.error
            return ToolResult(success=page.error is None, data=data, metadata=metadata)
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
