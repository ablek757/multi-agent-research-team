from typing import List

from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState


class SearchPlanner(BaseAgent):
    """搜索策划员：根据研究主题和当前状态生成搜索查询。"""

    name = "SearchPlanner"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback=None,
    ):
        super().__init__(config, progress_callback)

    def plan_queries(
        self,
        topic: str,
        state: ResearchState,
        count: int,
        language: str,
    ) -> List[str]:
        """生成初始或迭代的搜索查询。"""
        self._progress("正在规划搜索查询...")
        system = (
            "You are an expert research planner. Given a research topic and optionally "
            "what has been learned so far, generate diverse, specific, and high-value "
            "search queries to gather comprehensive information. "
            "Return ONLY a JSON object with a 'queries' key containing a list of strings."
        )
        lang_hint = "in Chinese" if language == "zh" else "in English"
        context = self._build_context(state)
        user = (
            f"Topic: {topic}\n\n"
            f"Current research context:\n{context}\n\n"
            f"Generate {count} search queries {lang_hint}."
        )
        content = self.complete(system, user, json_mode=True)
        queries = self.parse_json_list(content, "queries", count)
        self._progress(f"生成查询: {queries}")
        return queries

    def _build_context(self, state: ResearchState) -> str:
        lines = []
        if state.entities:
            lines.append(f"Key entities: {', '.join(state.entities[:30])}")
        if state.themes:
            lines.append(f"Themes: {', '.join(state.themes[:20])}")
        if state.gaps:
            lines.append("Information gaps:")
            for gap in state.gaps[:10]:
                lines.append(f"- {gap}")
        if state.open_questions:
            lines.append("Open questions:")
            for q in state.open_questions[:10]:
                lines.append(f"- {q}")
        if state.contradictions:
            lines.append("Noted contradictions:")
            for c in state.contradictions[:5]:
                desc = c.get("description", "")
                if desc:
                    lines.append(f"- {desc}")
        if not lines:
            lines.append("No prior context; start from the topic itself.")
        return "\n".join(lines)
