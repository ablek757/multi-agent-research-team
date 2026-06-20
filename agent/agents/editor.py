from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState


class Editor(BaseAgent):
    """编辑/审核员：审核报告质量，指出问题并提出修改意见。"""

    name = "Editor"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback=None,
    ):
        super().__init__(config, progress_callback)

    def review(
        self,
        topic: str,
        report_body: str,
        state: ResearchState,
        language: str,
    ) -> str:
        """审核报告并返回修改意见。"""
        self._progress("正在审核报告...")
        system = (
            "You are a critical research editor. Review the provided research report "
            "for logical consistency, factual support, clarity, balance, and completeness. "
            "Identify specific issues such as unsupported claims, missing context, "
            "uncited facts, one-sided arguments, unclear structure, or overlooked contradictions. "
            "Return a structured list of actionable revision suggestions. Be concise but specific."
        )
        lang_hint = "Write in Chinese." if language == "zh" else "Write in English."
        gaps_text = "\n".join(f"- {g}" for g in state.gaps[:10]) if state.gaps else "None noted"
        contradictions_text = (
            "\n".join(f"- {c.get('description', '')}" for c in state.contradictions[:5])
            if state.contradictions
            else "None noted"
        )
        user = (
            f"Topic: {topic}\n\n"
            f"Report to review:\n{report_body}\n\n"
            f"Remaining research gaps:\n{gaps_text}\n\n"
            f"Known contradictions:\n{contradictions_text}\n\n"
            f"Provide revision feedback. {lang_hint}"
        )
        feedback = self.complete(system, user)
        self._progress("审稿完成")
        return feedback
