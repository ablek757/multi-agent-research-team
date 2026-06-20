"""可信验证与溯源系统统一入口。"""

from typing import Dict, List, Tuple

from agent.config import LLMConfig
from agent.research_state import ResearchState

from .claim_extractor import ClaimExtractor
from .confidence_scorer import ConfidenceScorer
from .cross_validator import CrossValidator
from .evidence_collector import EvidenceCollector
from .hallucination_detector import HallucinationDetector
from .models import EvidenceChain
from .traceability_engine import TraceabilityEngine


class ResearchVerifier:
    """研究可信验证器：提取声明 → 收集证据 → 交叉验证 → 计算置信度 → 生成溯源报告。"""

    def __init__(
        self,
        llm_config: LLMConfig,
        max_claims: int = 10,
        progress_callback=None,
    ):
        self.max_claims = max_claims
        self.progress_callback = progress_callback or (lambda _: None)

        self.claim_extractor = ClaimExtractor(llm_config, progress_callback)
        self.evidence_collector = EvidenceCollector(progress_callback)
        self.cross_validator = CrossValidator(progress_callback)
        self.confidence_scorer = ConfidenceScorer()
        self.traceability_engine = TraceabilityEngine()
        self.hallucination_detector = HallucinationDetector(progress_callback)

    def verify(
        self,
        state: ResearchState,
        language: str = "zh",
    ) -> Tuple[List[EvidenceChain], Dict, str]:
        """对研究状态执行完整验证，返回证据链、幻觉检测结果、溯源报告。"""
        self.progress_callback("启动可信验证与溯源...")

        claims = self.claim_extractor.extract_claims(
            state,
            max_claims=self.max_claims,
            language=language,
        )

        evidence_map = self.evidence_collector.collect(state, claims)

        chains: List[EvidenceChain] = []
        for claim in claims:
            evidences = evidence_map.get(claim.id, [])
            signals = self.cross_validator.validate(state, evidences)
            score_result = self.confidence_scorer.score(signals)
            chain = self.traceability_engine.build_chain(
                claim=claim,
                evidences=evidences,
                score_result=score_result,
                signals=signals,
            )
            chains.append(chain)

        hallucination = self.hallucination_detector.detect(
            state.report_body or "",
            chains,
        )

        report = self.traceability_engine.render_markdown(chains, hallucination, language)
        self.progress_callback("可信验证与溯源完成")
        return chains, hallucination, report
