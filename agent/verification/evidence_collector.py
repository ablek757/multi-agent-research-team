"""为声明收集来源证据片段。"""

import re
from typing import Dict, List
from urllib.parse import urlparse

from agent.research_state import PageSummary, ResearchState

from .models import Claim, Evidence, EvidenceStance


class EvidenceCollector:
    """基于已有 PageSummary，为每个声明检索支持或反驳的证据片段。"""

    def __init__(self, progress_callback=None):
        self.progress_callback = progress_callback or (lambda _: None)

    def collect(
        self,
        state: ResearchState,
        claims: List[Claim],
    ) -> Dict[str, List[Evidence]]:
        """返回每个 claim id 对应的证据列表。"""
        self.progress_callback("正在为声明收集证据片段...")
        results: Dict[str, List[Evidence]] = {c.id: [] for c in claims}

        for claim in claims:
            keywords = self._extract_keywords(claim.text)
            if not keywords:
                continue

            for summary in state.summaries:
                evidence = self._collect_from_summary(claim, keywords, summary)
                if evidence:
                    results[claim.id].append(evidence)

        total = sum(len(v) for v in results.values())
        self.progress_callback(f"共收集到 {total} 条证据片段")
        return results

    def _collect_from_summary(
        self,
        claim: Claim,
        keywords: List[str],
        summary: PageSummary,
    ) -> Evidence | None:
        text = self._summary_text(summary)
        if not text:
            return None

        sentences = re.split(r"(?<=[。！？.!?])\s+", text)
        best_sentence = ""
        best_matches = 0

        for sentence in sentences:
            sentence_lower = sentence.lower()
            matches = sum(1 for kw in keywords if kw in sentence_lower)
            if matches > best_matches:
                best_matches = matches
                best_sentence = sentence.strip()

        if best_matches == 0:
            return None

        stance = self._detect_stance(best_sentence, keywords)
        relevance = max(1, min(10, int(best_matches / max(1, len(keywords)) * 10)))
        is_direct_quote = best_matches >= max(2, len(keywords) * 0.5) and len(best_sentence) >= 10

        return Evidence(
            source_index=summary.source_index,
            url=summary.url,
            title=summary.title,
            quote=best_sentence,
            context=text[:300].strip(),
            stance=stance,
            relevance_score=relevance,
            domain=self._extract_domain(summary.url),
            is_direct_quote=is_direct_quote,
        )

    def _summary_text(self, summary: PageSummary) -> str:
        parts = [summary.title, summary.summary]
        parts.extend(summary.key_findings)
        return "\n".join(p for p in parts if p)

    def _extract_keywords(self, text: str) -> List[str]:
        """提取中英文关键词：保留长度≥2 的连续中文词或英文/数字词。"""
        text_lower = text.lower()
        # 英文与数字词
        words = re.findall(r"[a-z0-9]{2,}", text_lower)
        # 连续中文字符（至少 2 个）
        chinese = re.findall(r"[\u4e00-\u9fa5]{2,}", text_lower)
        combined = words + chinese
        # 去重并保持一定顺序
        seen = set()
        result = []
        for w in combined:
            if w not in seen and len(w) >= 2:
                seen.add(w)
                result.append(w)
        return result[:8]

    def _detect_stance(self, sentence: str, keywords: List[str]) -> EvidenceStance:
        """简单启发式：若句子含常见否定词且包含关键词，则判为反驳。"""
        sentence_lower = sentence.lower()
        negation_patterns = [
            "不", "未", "无", "没有", "并非", "不是", "不对", "错误",
            "虚假", "谣言", "反驳", "否认", "否定", "contradict", "refute",
            "not ", "no ", "false", "incorrect", "misleading",
        ]
        has_negation = any(p in sentence_lower for p in negation_patterns)
        has_keyword = any(kw in sentence_lower for kw in keywords)
        if has_negation and has_keyword:
            return EvidenceStance.REFUTE
        return EvidenceStance.SUPPORT

    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc.lower()
        except Exception:
            return ""
