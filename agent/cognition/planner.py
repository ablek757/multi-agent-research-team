"""任务规划器：将研究主题拆分为子任务。"""

import json
import logging
import re
from datetime import datetime
from typing import List, Optional

from agent.cognition.models import Plan, SubTask
from agent.llm import LLMClient

logger = logging.getLogger(__name__)


class TaskPlanner:
    """基于 LLM 的研究任务规划器。"""

    def __init__(self, llm: LLMClient, max_subtasks: int = 5):
        self.llm = llm
        self.max_subtasks = max_subtasks

    def decompose(
        self,
        topic: str,
        context: str = "",
        related_summaries: Optional[List[str]] = None,
        language: str = "zh",
    ) -> Plan:
        """将主题拆分为可执行的子任务计划。"""
        system = (
            "你是一位研究规划专家。请将用户的研究主题拆分为若干可独立执行的子任务。\n"
            "要求：\n"
            "1. 每个子任务包含 id、description、goal、dependencies。\n"
            "2. dependencies 只能是之前子任务的 id，不能依赖未来任务。\n"
            "3. 子任务应覆盖：背景调研、核心概念、最新进展、关键争议、未来方向等。\n"
            "4. 输出严格为 JSON 列表。"
        )
        if language == "en":
            system = (
                "You are a research planning expert. Decompose the user's topic into independent subtasks.\n"
                "Requirements:\n"
                "1. Each subtask has id, description, goal, dependencies.\n"
                "2. dependencies can only reference previous subtask ids.\n"
                "3. Cover background, core concepts, latest progress, controversies, future directions.\n"
                "4. Output strictly as a JSON list."
            )

        related_text = ""
        if related_summaries:
            related_text = "\n相关历史研究摘要：\n" + "\n".join(
                f"- {s}" for s in related_summaries[:5]
            )

        user = f"研究主题：{topic}\n{related_text}\n{context}\n\n请生成不超过 {self.max_subtasks} 个子任务。"

        content = self.llm.complete(system=system, user=user)
        subtasks = self._parse_subtasks(content)
        if not subtasks:
            # 回退：生成一个单子任务
            subtasks = [
                SubTask(
                    id="t1",
                    description=f"综合研究 {topic}",
                    goal=f"产出关于 {topic} 的深度研究报告",
                )
            ]
        return Plan(topic=topic, subtasks=subtasks, max_iterations=3)

    def replan(
        self,
        plan: Plan,
        reflection_reasoning: str,
        language: str = "zh",
    ) -> Plan:
        """根据反思结果调整现有计划，可新增或修改子任务。"""
        system = (
            "你是一位研究规划专家。请根据反思结果调整研究计划。\n"
            "你可以：新增子任务、修改未开始子任务描述、标记需要重新搜索的子任务。\n"
            "输出严格为 JSON 列表，包含调整后的所有子任务。"
        )
        if language == "en":
            system = (
                "You are a research planning expert. Adjust the research plan based on reflection.\n"
                "You may add subtasks, modify pending ones, or mark tasks needing re-search.\n"
                "Output strictly as a JSON list."
            )

        plan_text = "\n".join(
            f"- [{s.status}] {s.id}: {s.description} (deps: {s.dependencies})"
            for s in plan.subtasks
        )
        user = f"反思：{reflection_reasoning}\n\n当前计划：\n{plan_text}\n\n请输出调整后的子任务列表。"

        content = self.llm.complete(system=system, user=user)
        new_subtasks = self._parse_subtasks(content)
        if new_subtasks:
            # 保留已完成子任务状态
            completed = {s.id: s for s in plan.subtasks if s.status == "completed"}
            for st in new_subtasks:
                if st.id in completed:
                    st.status = "completed"
                    st.result = completed[st.id].result
            plan.subtasks = new_subtasks
        plan.iteration += 1
        return plan

    def _parse_subtasks(self, content: str) -> List[SubTask]:
        """从 LLM 输出解析子任务列表。"""
        content = content.strip()
        # 尝试提取 JSON 代码块
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        try:
            data = json.loads(content)
            if isinstance(data, dict) and "subtasks" in data:
                data = data["subtasks"]
            if not isinstance(data, list):
                return []
            subtasks = []
            for i, item in enumerate(data[: self.max_subtasks]):
                if not isinstance(item, dict):
                    continue
                subtasks.append(
                    SubTask(
                        id=item.get("id") or f"t{i+1}",
                        description=item.get("description", ""),
                        goal=item.get("goal", ""),
                        dependencies=item.get("dependencies", []) or [],
                    )
                )
            return subtasks
        except Exception as exc:
            logger.warning("解析子任务失败: %s", exc)
            return []

    def _progress(self, message: str):
        logger.info(message)
