from typing import Dict, List

from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState, VerificationResult


class FactChecker(BaseAgent):
    """事实核查员：对关键发现进行交叉验证、可信度评分与风险标记。"""

    name = "FactChecker"

    def __init__(
        self,
        config: LLMConfig,
        progress_callback=None,
    ):
        super().__init__(config, progress_callback)

    def verify(
        self,
        topic: str,
        state: ResearchState,
        language: str,
        max_claims: int = 10,
    ) -> List[VerificationResult]:
        """对当前关键发现进行核查，返回核查结果列表。"""
        self._progress("正在核查关键发现的可信度...")
        claims = self._select_claims(state, max_claims)
        if not claims:
            self._progress("没有可核查的发现")
            return []

        system = (
            "You are a rigorous fact-checker. Given a research topic and a list of factual claims, "
            "evaluate each claim based on the provided source summaries. "
            "Return ONLY a JSON object with a 'verifications' key containing a list of objects. "
            "Each object must have:\n"
            "- claim: the claim being evaluated\n"
            "- credibility_score: integer 1-10 (10 = highly credible)\n"
            "- assessment: brief explanation of the evaluation\n"
            "- concerns: list of potential issues (bias, weak source, missing context, contradiction)"
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."

        summaries_text = "\n\n".join(
            f"Source [{s.source_index}] {s.title} ({s.url}):\n{s.summary}"
            for s in state.summaries[-20:]
        )
        claims_text = "\n".join(f"- {c}" for c in claims)
        user = (
            f"Topic: {topic}\n\n"
            f"Source summaries:\n{summaries_text}\n\n"
            f"Claims to verify:\n{claims_text}\n\n"
            f"Return structured JSON. {lang_hint}"
        )
        content = self.complete(system, user, json_mode=True)
        data = self.parse_json(content, {"verifications": []})
        raw_results = data.get("verifications", [])

        results: List[VerificationResult] = []
        for item in raw_results:
            if not isinstance(item, dict):
                continue
            claim = str(item.get("claim", "")).strip()
            if not claim:
                continue
            score = item.get("credibility_score", 5)
            try:
                score = int(score)
            except (TypeError, ValueError):
                score = 5
            score = max(1, min(10, score))
            assessment = str(item.get("assessment", "")).strip()
            concerns = item.get("concerns", [])
            if not isinstance(concerns, list):
                concerns = []
            concerns = [str(c) for c in concerns if c]

            # Collect source URLs that mention related terms (simple heuristic)
            sources = self._find_sources_for_claim(claim, state)
            results.append(
                VerificationResult(
                    claim=claim,
                    sources=sources,
                    credibility_score=score,
                    assessment=assessment,
                    concerns=concerns,
                )
            )

        state.verification_results = results
        self._progress(f"完成核查: {len(results)} 条发现")
        return results

    def _select_claims(self, state: ResearchState, max_claims: int) -> List[str]:
        """选择最值得核查的发现。"""
        claims = []
        seen = set()
        for finding in state.findings:
            key = finding.lower().strip()
            if key and key not in seen:
                seen.add(key)
                claims.append(finding)
            if len(claims) >= max_claims:
                break
        return claims

    def _find_sources_for_claim(self, claim: str, state: ResearchState) -> List[str]:
        """简单启发式：返回与声明关键词相关的来源 URL。"""
        keywords = [w for w in claim.lower().split() if len(w) > 3]
        matched = []
        for summary in state.summaries:
            text = (summary.title + " " + summary.summary).lower()
            if any(kw in text for kw in keywords[:3]):
                matched.append(summary.url)
        return matched[:3]
