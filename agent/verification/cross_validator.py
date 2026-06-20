"""多源交叉验证：评估不同来源对声明的一致性与支持力度。"""

from typing import Dict, List

from agent.research_state import ResearchState

from .models import Evidence, EvidenceStance


class CrossValidator:
    """对单个声明的证据集合进行交叉验证，输出多维信号。"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback or (lambda _: None)

    def validate(
        self,
        state: ResearchState,
        evidences: List[Evidence],
    ) -> Dict:
        """返回交叉验证信号字典。"""
        support = [e for e in evidences if e.stance == EvidenceStance.SUPPORT]
        refute = [e for e in evidences if e.stance == EvidenceStance.REFUTE]
        neutral = [e for e in evidences if e.stance == EvidenceStance.NEUTRAL]

        support_domains = {e.domain for e in support if e.domain}
        refute_domains = {e.domain for e in refute if e.domain}

        direct_quotes = sum(1 for e in evidences if e.is_direct_quote)
        avg_relevance = (
            sum(e.relevance_score for e in evidences) / len(evidences)
            if evidences else 0.0
        )

        # 立场一致性：支持证据占比
        total_positions = len(support) + len(refute)
        if total_positions == 0:
            agreement = 0.0
        else:
            agreement = len(support) / total_positions

        # 是否发现与声明相关的已有矛盾
        contradiction_hints = self._find_contradictions(state, evidences)

        return {
            "supporting_count": len(support),
            "refuting_count": len(refute),
            "neutral_count": len(neutral),
            "support_domains": sorted(support_domains),
            "refute_domains": sorted(refute_domains),
            "unique_domain_count": len(support_domains | refute_domains),
            "direct_quote_count": direct_quotes,
            "average_relevance": avg_relevance,
            "agreement_ratio": agreement,
            "contradiction_hints": contradiction_hints,
        }

    def _find_contradictions(
        self,
        state: ResearchState,
        evidences: List[Evidence],
    ) -> List[str]:
        """从 Analyst 已发现的矛盾中，寻找与当前证据来源相关的提示。"""
        hints = []
        evidence_urls = {e.url for e in evidences}
        for contradiction in state.contradictions:
            desc = contradiction.get("description", "")
            sources_hint = contradiction.get("sources_hint", "")
            if not desc:
                continue
            # 若矛盾描述涉及任一证据域名，或 Analyst 给出的 sources_hint 非空，则记录
            if sources_hint or any(e.domain in desc for e in evidences):
                hints.append(desc)
        return hints
