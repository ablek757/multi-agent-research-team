"""研究报告质量评估器。"""

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set
from urllib.parse import urlparse

from agent.config import Config
from agent.llm import LLMClient
from agent.research_state import ResearchState

logger = logging.getLogger(__name__)


@dataclass
class ReportMetrics:
    """报告质量指标。"""

    source_count: int = 0
    domain_diversity: int = 0
    citation_coverage: float = 0.0
    claim_source_alignment: float = 0.0
    length_score: float = 0.0
    hallucination_risk: float = 0.0
    overall_score: float = 0.0
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_count": self.source_count,
            "domain_diversity": self.domain_diversity,
            "citation_coverage": round(self.citation_coverage, 3),
            "claim_source_alignment": round(self.claim_source_alignment, 3),
            "length_score": round(self.length_score, 3),
            "hallucination_risk": round(self.hallucination_risk, 3),
            "overall_score": round(self.overall_score, 3),
            "details": self.details,
        }


class ReportEvaluator:
    """自动评估研究报告质量。"""

    def __init__(self, config: Config):
        self.config = config
        self.llm = LLMClient(config.llm)

    def evaluate(self, topic: str, state: ResearchState, report_body: str) -> ReportMetrics:
        """评估报告并返回指标。"""
        metrics = ReportMetrics()
        metrics.source_count = len(state.sources)
        metrics.domain_diversity = self._domain_diversity(state.sources)
        metrics.citation_coverage = self._citation_coverage(report_body, state.sources)
        metrics.claim_source_alignment = self._claim_alignment(report_body, state)
        metrics.length_score = self._length_score(report_body)
        metrics.hallucination_risk = self._hallucination_risk(report_body, state)

        # 综合得分（加权）
        metrics.overall_score = self._overall_score(metrics)

        # LLM 辅助评估
        try:
            llm_metrics = self._llm_evaluate(topic, report_body, state)
            metrics.details.update(llm_metrics)
        except Exception as exc:
            logger.warning("LLM 质量评估失败: %s", exc)

        return metrics

    def _domain_diversity(self, sources) -> int:
        domains: Set[str] = set()
        for s in sources:
            try:
                netloc = urlparse(s.url).netloc
                if netloc:
                    domains.add(netloc)
            except Exception:
                continue
        return len(domains)

    def _citation_coverage(self, report_body: str, sources) -> float:
        """计算正文中引用了多少个来源。"""
        if not sources:
            return 0.0
        cited = set()
        for s in sources:
            if re.search(rf"\[\s*{s.index}\s*\]", report_body):
                cited.add(s.index)
        return len(cited) / len(sources)

    def _claim_alignment(self, report_body: str, state: ResearchState) -> float:
        """粗略估算关键声明与来源数量之比。"""
        if not state.findings:
            return 0.0
        # 每个 finding 若被报告正文提及，则认为对齐
        aligned = 0
        for finding in state.findings:
            key_phrase = finding[:30]
            if key_phrase and key_phrase in report_body:
                aligned += 1
        return aligned / len(state.findings)

    def _length_score(self, report_body: str) -> float:
        """根据字数给出长度分。"""
        length = len(report_body)
        if length < 500:
            return 0.3
        if length < 1500:
            return 0.6
        if length < 3000:
            return 0.85
        return 1.0

    def _hallucination_risk(self, report_body: str, state: ResearchState) -> float:
        """基于未引用数字/声明数量估算幻觉风险。"""
        if not report_body:
            return 1.0
        # 统计未带引用标记的数字声明
        suspicious = 0
        sentences = re.split(r"(?<=[。！？.!?])\s+", report_body)
        for sentence in sentences:
            if re.search(r"\d", sentence) and not re.search(r"\[\d+\]", sentence):
                suspicious += 1
        total = len(sentences) or 1
        risk = suspicious / total
        # 来源越多风险越低
        if state.sources:
            risk *= max(0.5, 1 - len(state.sources) * 0.05)
        return min(1.0, risk)

    def _overall_score(self, metrics: ReportMetrics) -> float:
        weights = {
            "source_count": 0.15,
            "domain_diversity": 0.15,
            "citation_coverage": 0.20,
            "claim_alignment": 0.15,
            "length": 0.15,
            "hallucination": 0.20,
        }
        source_score = min(1.0, metrics.source_count / 5)
        diversity_score = min(1.0, metrics.domain_diversity / 3)
        hallucination_score = 1.0 - metrics.hallucination_risk

        overall = (
            weights["source_count"] * source_score
            + weights["domain_diversity"] * diversity_score
            + weights["citation_coverage"] * metrics.citation_coverage
            + weights["claim_alignment"] * metrics.claim_source_alignment
            + weights["length"] * metrics.length_score
            + weights["hallucination"] * hallucination_score
        )
        return overall

    def _llm_evaluate(self, topic: str, report_body: str, state: ResearchState) -> Dict[str, Any]:
        """使用 LLM 给出定性质量评估。"""
        system = (
            "你是一位研究质量评估专家。请评估以下研究报告，输出 JSON，包含：\n"
            "- strengths: 优点列表\n"
            "- weaknesses: 缺点列表\n"
            "- coherence_score（1-10）\n"
            "- factual_risk_score（1-10，越高风险越大）\n"
            "- recommendations: 改进建议列表"
        )
        user = (
            f"主题：{topic}\n\n"
            f"报告：\n{report_body[:6000]}\n\n"
            f"来源数：{len(state.sources)}，发现数：{len(state.findings)}"
        )
        content = self.llm.complete(system=system, user=user)
        match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if match:
            content = match.group(1).strip()
        return json.loads(content)
