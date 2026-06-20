"""元认知反思 Agent：监控研究质量并给出调整建议。"""

import json
import logging
import re
from typing import List

from agent.cognition.models import Reflection
from agent.llm import LLMClient
from agent.research_state import ResearchState

logger = logging.getLogger(__name__)


class MetaCritic:
    """对研究状态进行反思，发现信息缺口、来源偏见和计划偏差。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def reflect(
        self,
        topic: str,
        state: ResearchState,
        plan_summary: str = "",
        language: str = "zh",
    ) -> Reflection:
        """基于当前研究状态输出反思结果。"""
        system = (
            "你是一位严苛的研究质量审查者。请根据当前研究状态进行元认知反思。\n"
            "输出严格为 JSON，包含以下字段：\n"
            "- information_gaps: 信息缺口列表\n"
            "- source_bias_notes: 来源偏见或可靠性问题列表\n"
            "- plan_deviation: 计划执行偏差描述\n"
            "- suggested_queries: 为填补缺口建议的搜索查询列表\n"
            "- should_replan: 是否需要重规划（true/false）\n"
            "- reasoning: 简要推理过程"
        )
        if language == "en":
            system = (
                "You are a rigorous research quality reviewer. Reflect on the current research state.\n"
                "Output strictly as JSON with fields:\n"
                "- information_gaps\n"
                "- source_bias_notes\n"
                "- plan_deviation\n"
                "- suggested_queries\n"
                "- should_replan (true/false)\n"
                "- reasoning"
            )

        state_summary = self._summarize_state(state)
        user = f"研究主题：{topic}\n\n当前计划摘要：\n{plan_summary}\n\n研究状态：\n{state_summary}\n\n请输出反思 JSON。"

        content = self.llm.complete(system=system, user=user)
        return self._parse_reflection(content)

    def _summarize_state(self, state: ResearchState) -> str:
        lines = []
        lines.append(f"已收集来源数：{len(state.sources)}")
        lines.append(f"已摘要页面数：{len(state.summaries)}")
        lines.append(f"已发现关键发现：{len(state.findings)}")
        if state.findings:
            lines.append("关键发现：")
            for f in state.findings[:10]:
                lines.append(f"- {f}")
        if state.gaps:
            lines.append("当前信息缺口：")
            for g in state.gaps:
                lines.append(f"- {g}")
        if state.verification_results:
            low = [v for v in state.verification_results if getattr(v, "credibility_score", 10) < 6]
            if low:
                lines.append(f"低可信度声明数：{len(low)}")
        return "\n".join(lines)

    def _parse_reflection(self, content: str) -> Reflection:
        content = content.strip()
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        try:
            data = json.loads(content)
            return Reflection(
                information_gaps=_as_list(data.get("information_gaps", [])),
                source_bias_notes=_as_list(data.get("source_bias_notes", [])),
                plan_deviation=data.get("plan_deviation", ""),
                suggested_queries=_as_list(data.get("suggested_queries", [])),
                should_replan=bool(data.get("should_replan", False)),
                reasoning=data.get("reasoning", ""),
            )
        except Exception as exc:
            logger.warning("解析反思结果失败: %s", exc)
            return Reflection(reasoning="解析失败，使用默认继续策略")


def _as_list(value) -> List[str]:
    if isinstance(value, list):
        return [str(v) for v in value]
    if value:
        return [str(value)]
    return []
