"""日期时间工具：获取当前时间和解析自然语言日期。"""

from datetime import datetime, timezone
from typing import Any, Dict

import dateparser
from agent.tools.base import BaseTool, ToolResult


class DateTool(BaseTool):
    """获取当前时间或解析自然语言日期表达式。"""

    name = "date"
    description = "获取当前日期时间，或将自然语言日期（如'昨天'、'2024年5月'）解析为 ISO 格式。"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["now", "parse"],
                "description": "动作：now 获取当前时间，parse 解析日期文本",
            },
            "text": {
                "type": "string",
                "description": "要解析的日期文本（parse 时使用）",
            },
            "language": {
                "type": "string",
                "description": "日期文本语言（parse 时使用）",
                "default": "zh",
            },
        },
        "required": ["action"],
    }

    def run(self, action: str, text: str = "", language: str = "zh") -> ToolResult:
        try:
            if action == "now":
                now = datetime.now(timezone.utc)
                data: Dict[str, Any] = {
                    "iso": now.isoformat(),
                    "local_iso": datetime.now().isoformat(),
                    "timestamp": now.timestamp(),
                }
                return ToolResult(success=True, data=data)

            if action == "parse":
                parsed = dateparser.parse(text, languages=[language])
                if parsed is None:
                    return ToolResult(success=False, error=f"Could not parse date: {text}")
                return ToolResult(
                    success=True,
                    data={
                        "text": text,
                        "iso": parsed.isoformat(),
                        "timestamp": parsed.timestamp(),
                    },
                )

            return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(success=False, error=str(exc))
