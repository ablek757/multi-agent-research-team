from typing import List

from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState, VerificationResult


class Writer(BaseAgent):
    """撰稿员：基于验证后的研究发现撰写结构化 Markdown 报告。"""

    name = "Writer"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback=None,
    ):
        super().__init__(config, progress_callback)

    def write(
        self,
        topic: str,
        state: ResearchState,
        language: str,
    ) -> str:
        """撰写报告初稿。"""
        self._progress("正在撰写报告初稿...")
        system = (
            "You are a senior research writer. Write a structured, in-depth research report "
            "in Markdown format. Use clear sections, bullet points, and paragraphs. "
            "Be factual and base all claims on the provided findings. "
            "Cite sources inline using [n] notation where n corresponds to the source index. "
            "Acknowledge uncertainties and contradictions where they exist."
        )
        lang_hint = "Write in Chinese." if language == "zh" else "Write in English."
        user = self._build_prompt(topic, state, lang_hint)
        report = self.complete(system, user)
        self._progress("报告初稿完成")
        return report

    def revise(
        self,
        topic: str,
        report_body: str,
        feedback: str,
        state: ResearchState,
        language: str,
    ) -> str:
        """根据编辑反馈修订报告。"""
        self._progress("正在根据审稿意见修订报告...")
        system = (
            "You are a senior research writer. Revise the provided research report "
            "based on the editor's feedback. Preserve the Markdown structure and source citations. "
            "Address every specific issue raised; if you disagree, explain why."
        )
        lang_hint = "Write in Chinese." if language == "zh" else "Write in English."
        user = (
            f"Topic: {topic}\n\n"
            f"Original report:\n{report_body}\n\n"
            f"Editor feedback:\n{feedback}\n\n"
            f"Please produce the revised report. {lang_hint}"
        )
        revised = self.complete(system, user)
        self._progress("报告修订完成")
        return revised

    def _build_prompt(self, topic: str, state: ResearchState, lang_hint: str) -> str:
        sources_text = "\n".join(
            f"[{s.index}] {s.title} - {s.url}" for s in state.sources
        )
        verifications_text = self._format_verifications(state.verification_results)
        connections_text = self._format_connections(state.connections)
        contradictions_text = self._format_contradictions(state.contradictions)

        user = (
            f"Topic: {topic}\n\n"
            f"Findings:\n" + "\n".join(f"- {f}" for f in state.findings[-80:]) + "\n\n"
            f"Key entities: {', '.join(state.entities[:50])}\n\n"
            f"Themes: {', '.join(state.themes[:20])}\n\n"
        )
        if connections_text:
            user += f"Connections & implications:\n{connections_text}\n\n"
        if contradictions_text:
            user += f"Contradictions & uncertainties:\n{contradictions_text}\n\n"
        if verifications_text:
            user += f"Fact-checking notes:\n{verifications_text}\n\n"
        if state.gaps:
            user += "Remaining gaps:\n" + "\n".join(f"- {g}" for g in state.gaps[:10]) + "\n\n"
        user += (
            f"Sources:\n{sources_text}\n\n"
            f"Write the report with these sections:\n"
            f"1. Executive Summary\n"
            f"2. Background / Context\n"
            f"3. Key Findings\n"
            f"4. Connections & Implications\n"
            f"5. Fact-Checking & Credibility Assessment\n"
            f"6. Open Questions & Limitations\n"
            f"7. Conclusion\n\n"
            f"{lang_hint}"
        )
        return user

    def _format_verifications(self, results: List[VerificationResult]) -> str:
        if not results:
            return ""
        lines = []
        for v in results:
            lines.append(
                f"- Claim: {v.claim}\n"
                f"  Credibility: {v.credibility_score}/10\n"
                f"  Assessment: {v.assessment}\n"
                f"  Concerns: {', '.join(v.concerns) if v.concerns else 'None'}"
            )
        return "\n".join(lines)

    def _format_connections(self, connections: List[dict]) -> str:
        if not connections:
            return ""
        return "\n".join(
            f"- {c.get('description', '')}" for c in connections if c.get("description")
        )

    def _format_contradictions(self, contradictions: List[dict]) -> str:
        if not contradictions:
            return ""
        return "\n".join(
            f"- {c.get('description', '')}" for c in contradictions if c.get("description")
        )
