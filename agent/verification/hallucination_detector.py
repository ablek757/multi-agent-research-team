"""幻觉检测：定位报告中缺乏证据支持的声明。"""

import re
from typing import Dict, List

from .models import EvidenceChain, VerificationVerdict


class HallucinationDetector:
    """扫描报告正文，识别可能无证据支持的事实性句子。"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback or (lambda _: None)

    def detect(
        self,
        report_body: str,
        evidence_chains: List[EvidenceChain],
    ) -> Dict:
        """返回幻觉风险评分与问题片段列表。"""
        self.progress_callback("正在检测报告中的幻觉风险...")

        sentences = re.split(r"(?<=[。！？.!?])\s+", report_body)
        # 过滤掉标题、空行
        sentences = [s.strip() for s in sentences if s.strip() and not s.strip().startswith("#")]

        supported_claims = self._supported_claims(evidence_chains)

        flagged: List[Dict] = []
        factual_count = 0

        for sentence in sentences:
            if not self._is_factual_sentence(sentence):
                continue
            factual_count += 1

            if self._has_citation(sentence):
                continue

            if self._matches_supported_claim(sentence, supported_claims):
                continue

            flagged.append(
                {
                    "sentence": sentence,
                    "reason": "该事实性句子缺少引用且未找到对应的支持证据",
                }
            )

        risk_score = len(flagged) / max(1, factual_count)

        self.progress_callback(f"幻觉风险: {risk_score:.2%}")
        return {
            "risk_score": round(risk_score, 3),
            "factual_sentences": factual_count,
            "flagged_count": len(flagged),
            "flagged_sentences": flagged,
        }

    def _supported_claims(self, evidence_chains: List[EvidenceChain]) -> List[str]:
        """提取已验证或较可信的声明文本。"""
        supported = []
        for chain in evidence_chains:
            if chain.verdict in (VerificationVerdict.VERIFIED, VerificationVerdict.PLAUSIBLE):
                supported.append(chain.claim.text)
        return supported

    def _is_factual_sentence(self, sentence: str) -> bool:
        """判断句子是否包含事实性信息。"""
        # 包含数字、百分比、年份、常见量化/变化词
        patterns = [
            r"\d",
            r"%",
            r"\b(?:year|years|million|billion|percent)\b",
            r"年|月|日",
            r"增长|下降|增加|减少|达到|超过|约|达到|占比|上升至|下降至",
        ]
        return any(re.search(p, sentence) for p in patterns)

    def _has_citation(self, sentence: str) -> bool:
        return bool(re.search(r"\[\s*\d+\s*\]", sentence))

    def _matches_supported_claim(self, sentence: str, supported_claims: List[str]) -> bool:
        """简单重叠：若句子与任一已支持声明共享较多关键词，则认为有证据。"""
        sentence_lower = sentence.lower()
        for claim in supported_claims:
            claim_lower = claim.lower()
            # 子串包含
            if claim_lower in sentence_lower or sentence_lower in claim_lower:
                return True
            # 关键词重叠比例
            claim_keywords = set(self._tokenize(claim_lower))
            sent_keywords = set(self._tokenize(sentence_lower))
            if not claim_keywords:
                continue
            overlap = len(claim_keywords & sent_keywords) / len(claim_keywords)
            if overlap >= 0.5:
                return True
        return False

    def _tokenize(self, text: str) -> List[str]:
        # 保留中文词（长度≥2）和英文/数字词
        tokens = re.findall(r"[a-z0-9]{2,}|[\u4e00-\u9fa5]{2,}", text)
        return [t for t in tokens if len(t) >= 2]
