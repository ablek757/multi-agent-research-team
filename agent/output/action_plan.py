"""可执行方案看板格式器：将研究发现转化为行动项。"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List

from agent.config import Config
from agent.output.base import OutputArtifact, OutputFormatter
from agent.research_state import ResearchState


class ActionPlanFormatter(OutputFormatter):
    """将研究结论转化为 Markdown/HTML 可执行方案看板。"""

    name = "action_plan"
    mime_type = "text/markdown"
    extension = ".md"

    def format(self, topic: str, state: ResearchState) -> OutputArtifact:
        report_body = self._build_report_body(topic, state)
        items = self._extract_action_items(report_body, state)

        if not items:
            items = [
                {
                    "task": f"深化 {topic} 研究",
                    "owner": "研究员",
                    "priority": "高",
                    "dependency": "-",
                    "timeline": "1-2 周",
                    "rationale": "主题复杂，需进一步调研",
                }
            ]

        max_items = self.config.output.action_plan_max_items
        items = items[:max_items]

        lines = [
            f"# {topic} — 可执行方案看板",
            "",
            "| 任务 | 负责人 | 优先级 | 依赖 | 时间线 | 依据 |",
            "|------|--------|--------|------|--------|------|",
        ]
        for item in items:
            lines.append(
                f"| {item['task']} | {item['owner']} | {item['priority']} | "
                f"{item['dependency']} | {item['timeline']} | {item['rationale']} |"
            )

        lines.extend(["", "## 行动项详情", ""])
        for idx, item in enumerate(items, 1):
            lines.extend(
                [
                    f"### {idx}. {item['task']}",
                    f"- **负责人**：{item['owner']}",
                    f"- **优先级**：{item['priority']}",
                    f"- **依赖**：{item['dependency']}",
                    f"- **时间线**：{item['timeline']}",
                    f"- **依据**：{item['rationale']}",
                    "",
                ]
            )

        content = "\n".join(lines)
        file_path = str(Path(self.config.report.output_dir) / f"{self._safe_name(topic)}_action_plan.md")
        Path(self.config.report.output_dir).mkdir(parents=True, exist_ok=True)
        Path(file_path).write_text(content, encoding="utf-8")

        return OutputArtifact(
            format=self.name,
            content=content,
            file_path=file_path,
            mime_type=self.mime_type,
            metadata={"item_count": len(items)},
        )

    def _extract_action_items(self, report_body: str, state: ResearchState) -> List[Dict[str, Any]]:
        """使用 LLM 从报告中抽取行动项。"""
        from agent.llm import LLMClient

        llm = LLMClient(self.config.llm)
        system = (
            "你是一位战略执行顾问。请根据以下研究报告，提炼出可执行的行动方案。\n"
            "输出严格为 JSON 列表，每项包含：task, owner, priority（高/中/低）, dependency, timeline, rationale。\n"
            "最多输出 10 项。"
        )
        user = f"研究主题与报告：\n\n{report_body[:8000]}\n\n请输出行动方案 JSON。"
        try:
            content = llm.complete(system=system, user=user)
            return self._parse_items(content)
        except Exception as exc:
            return []

    def _parse_items(self, content: str) -> List[Dict[str, Any]]:
        content = content.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        try:
            data = json.loads(content)
            if isinstance(data, list):
                return [self._normalize_item(item) for item in data if isinstance(item, dict)]
        except Exception:
            pass
        return []

    def _normalize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "task": str(item.get("task", "")),
            "owner": str(item.get("owner", "TBD")),
            "priority": str(item.get("priority", "中")),
            "dependency": str(item.get("dependency", item.get("dependencies", "-"))),
            "timeline": str(item.get("timeline", "待定")),
            "rationale": str(item.get("rationale", "")),
        }

    def _safe_name(self, topic: str) -> str:
        return re.sub(r'[\\/:*?"<>|]+', "_", topic)[:50]
