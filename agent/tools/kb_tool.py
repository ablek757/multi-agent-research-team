"""知识库查询工具：让 Agent 能检索已有研究成果。"""

from typing import Any, Dict, List, Optional

from kb import KnowledgeStore
from agent.tools.base import BaseTool, ToolResult


class KBQueryTool(BaseTool):
    """查询知识库中的历史报告、实体、主题和统计信息。"""

    name = "kb_query"
    description = "查询知识库：全文搜索报告、获取统计信息、列出最近报告或查找相关研究。"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "stats", "list", "get"],
                "description": "查询动作",
            },
            "query": {
                "type": "string",
                "description": "搜索关键词（search 时使用）",
            },
            "report_id": {
                "type": "string",
                "description": "报告 ID（get 时使用）",
            },
            "limit": {
                "type": "integer",
                "description": "返回数量限制",
                "default": 10,
            },
        },
        "required": ["action"],
    }

    def __init__(self, **deps):
        super().__init__(**deps)
        self.kb_store: Optional[KnowledgeStore] = deps.get("kb_store")

    def run(
        self,
        action: str,
        query: str = "",
        report_id: str = "",
        limit: int = 10,
    ) -> ToolResult:
        if self.kb_store is None:
            return ToolResult(success=False, error="KB store not available")

        try:
            if action == "search":
                results = self.kb_store.search_reports(query, top_k=limit)
                data: List[Dict[str, Any]] = [
                    {
                        "report_id": item["report"].get("id"),
                        "title": item["report"].get("title"),
                        "score": item["score"],
                        "summary": item["report"].get("summary", "")[:300],
                    }
                    for item in results
                ]
                return ToolResult(success=True, data=data)

            if action == "stats":
                return ToolResult(success=True, data=self.kb_store.get_stats())

            if action == "list":
                return ToolResult(success=True, data=self.kb_store.list_reports(limit=limit))

            if action == "get":
                report = self.kb_store.get_report(report_id)
                if report is None:
                    return ToolResult(success=False, error=f"Report not found: {report_id}")
                return ToolResult(success=True, data=report.to_storage())

            return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
