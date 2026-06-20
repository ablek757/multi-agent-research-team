from typing import Dict, List

from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState


class Analyst(BaseAgent):
    """分析员：跨来源综合信息，发现主题、关联、矛盾与缺口。"""

    name = "Analyst"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback=None,
    ):
        super().__init__(config, progress_callback)

    def analyze(
        self,
        topic: str,
        state: ResearchState,
        language: str,
    ) -> Dict:
        """分析当前收集的信息，返回并更新 themes/connections/contradictions/gaps。"""
        self._progress("正在分析跨来源关联...")
        system = (
            "You are a senior research analyst. Given a set of findings and entities, "
            "identify overarching themes, connections, causal chains, contradictions, "
            "and remaining information gaps. Be critical and precise. "
            "Return ONLY a JSON object with these keys:\n"
            "- themes: list of major themes\n"
            "- connections: list of connections, each with 'description' and optional 'entities'\n"
            "- contradictions: list of contradictions, each with 'description' and 'sources_hint'\n"
            "- gaps: list of remaining information gaps or open questions to investigate"
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."
        user = (
            f"Topic: {topic}\n\n"
            f"Findings:\n" + "\n".join(f"- {f}" for f in state.findings[-50:]) + "\n\n"
            f"Entities: {', '.join(state.entities[:40])}\n\n"
            f"Open questions:\n" + "\n".join(f"- {q}" for q in state.open_questions[:20]) + "\n\n"
            f"Analyze and return structured JSON. {lang_hint}"
        )
        content = self.complete(system, user, json_mode=True)
        result = self.parse_json(
            content,
            {
                "themes": [],
                "connections": [],
                "contradictions": [],
                "gaps": [],
            },
        )

        # Normalize fields
        for key in ("themes", "connections", "contradictions", "gaps"):
            value = result.get(key)
            if not isinstance(value, list):
                result[key] = []

        # Update state
        state.themes = [str(t) for t in result["themes"] if t]
        state.connections = [c for c in result["connections"] if isinstance(c, dict)]
        state.contradictions = [c for c in result["contradictions"] if isinstance(c, dict)]
        state.gaps = [str(g) for g in result["gaps"] if g]

        self._progress(
            f"分析完成: {len(state.themes)} 个主题, "
            f"{len(state.connections)} 个关联, "
            f"{len(state.contradictions)} 个矛盾, "
            f"{len(state.gaps)} 个缺口"
        )
        return result
