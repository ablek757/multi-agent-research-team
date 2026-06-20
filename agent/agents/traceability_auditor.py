"""可追溯审计员：为报告结论建立证据链并触发低可信度结论修订。"""

from typing import Optional

from agent.agents.base import BaseAgent
from agent.agents.writer import Writer
from agent.config import Config, LLMConfig
from agent.research_state import ResearchState
from agent.verification import ResearchVerifier
from agent.verification.models import VerificationVerdict


class TraceabilityAuditor(BaseAgent):
    """TraceabilityAuditor：可信验证与溯源审计员。

    在撰稿完成后运行，为每个关键结论建立证据链、计算置信度、检测幻觉风险，
    并在配置允许时，将低可信度结论反馈给 Writer 进行修订。
    """

    name = "TraceabilityAuditor"

    def __init__(
        self,
        llm_config: LLMConfig,
        verification_config: Optional["VerificationConfig"] = None,
        progress_callback=None,
    ):
        super().__init__(llm_config, progress_callback)
        self.verification_config = verification_config
        max_claims = getattr(verification_config, "max_claims", 10)
        self.verifier = ResearchVerifier(
            llm_config=llm_config,
            max_claims=max_claims,
            progress_callback=progress_callback,
        )

    def audit(
        self,
        topic: str,
        state: ResearchState,
        language: str = "zh",
    ) -> str:
        """执行审计，将证据链与溯源报告写入 state，返回溯源报告。"""
        self._progress("正在为报告结论建立可追溯证据链...")

        chains, hallucination, report = self.verifier.verify(state, language)
        state.evidence_chains = chains
        state.traceability_report = report
        state.hallucination_risk = hallucination.get("risk_score", 0.0)

        verified = sum(1 for c in chains if c.verdict == VerificationVerdict.VERIFIED)
        unsupported = sum(
            1 for c in chains if c.verdict == VerificationVerdict.UNSUPPORTED
        )
        self._progress(
            f"审计完成：{len(chains)} 条声明，{verified} 条已验证，{unsupported} 条未证实，"
            f"幻觉风险 {state.hallucination_risk:.1%}"
        )
        return report

    def maybe_revise(
        self,
        topic: str,
        state: ResearchState,
        language: str = "zh",
        style_profile=None,
    ) -> str:
        """如果存在低置信度声明且配置允许，则生成修订反馈并调用 Writer 修订。"""
        if not self.verification_config:
            return state.report_body

        if not getattr(self.verification_config, "enable_auto_revision", False):
            return state.report_body

        threshold = getattr(self.verification_config, "confidence_threshold", 50)
        low_confidence_chains = [
            c for c in state.evidence_chains if c.confidence_score < threshold
        ]

        if not low_confidence_chains and state.hallucination_risk < 0.2:
            self._progress("未发现需要因可信度问题而修订的结论")
            return state.report_body

        feedback = self._build_revision_feedback(low_confidence_chains, state)
        self._progress(f"发现 {len(low_confidence_chains)} 条低可信度结论，触发自动修订...")

        writer = Writer(self.config)
        revised = writer.revise(
            topic=topic,
            report_body=state.report_body,
            feedback=feedback,
            state=state,
            language=language,
            style_profile=style_profile,
        )
        state.report_body = revised
        state.revisions.append(
            {
                "round": "traceability",
                "feedback": feedback,
                "before": state.report_body,
                "after": revised,
            }
        )
        self._progress("已完成基于可信验证的修订")
        return revised

    def _build_revision_feedback(
        self,
        low_confidence_chains,
        state: ResearchState,
    ) -> str:
        lines = [
            "基于可信验证与溯源审计，请重点修订以下低可信度或高风险结论：",
            "",
        ]
        for chain in low_confidence_chains:
            lines.append(
                f"- 声明：{chain.claim.text}\n"
                f"  置信度：{chain.confidence_score}/100（{chain.confidence_label}）\n"
                f"  风险：{'; '.join(chain.concerns) if chain.concerns else '证据不足'}"
            )
        if state.hallucination_risk >= 0.2:
            lines.append(
                f"\n此外，报告整体幻觉风险为 {state.hallucination_risk:.1%}，"
                "请为无来源支持的事实性陈述补充引用或删除。"
            )
        return "\n".join(lines)
