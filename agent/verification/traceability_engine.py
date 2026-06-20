"""证据链组装与溯源报告生成。"""

from typing import Dict, List

from .models import Claim, Evidence, EvidenceChain

_LABEL_LOCALE = {
    "已验证": {"zh": "已验证", "en": "Verified"},
    "较可信": {"zh": "较可信", "en": "Plausible"},
    "存在争议": {"zh": "存在争议", "en": "Contested"},
    "未证实": {"zh": "未证实", "en": "Unsupported"},
    "被反驳": {"zh": "被反驳", "en": "Refuted"},
}

_STANCE_LOCALE = {
    "support": {"zh": "支持", "en": "Support"},
    "refute": {"zh": "反驳", "en": "Refute"},
    "neutral": {"zh": "中立", "en": "Neutral"},
}


class TraceabilityEngine:
    """将声明、证据、交叉验证信号组装为可追溯的证据链，并生成报告。"""

    def build_chain(
        self,
        claim: Claim,
        evidences: List[Evidence],
        score_result: Dict,
        signals: Dict,
    ) -> EvidenceChain:
        """组装单个声明的证据链。"""
        return EvidenceChain(
            claim=claim,
            evidences=evidences,
            verdict=score_result["verdict"],
            confidence_score=score_result["score"],
            confidence_label=score_result["label"],
            supporting_count=signals.get("supporting_count", 0),
            refuting_count=signals.get("refuting_count", 0),
            unique_domains=signals.get("support_domains", []),
            assessment=self._build_assessment(claim, score_result, signals),
            concerns=score_result.get("concerns", []),
        )

    def _build_assessment(self, claim: Claim, score_result: Dict, signals: Dict) -> str:
        label = score_result["label"]
        support = signals.get("supporting_count", 0)
        refute = signals.get("refuting_count", 0)
        domains = signals.get("unique_domain_count", 0)
        quotes = signals.get("direct_quote_count", 0)
        return (
            f"结论“{claim.text[:40]}...”被评为“{label}”。"
            f"支持来源 {support} 个，反驳来源 {refute} 个，"
            f"覆盖 {domains} 个不同域名，包含 {quotes} 条直接引用。"
        )

    def render_markdown(
        self,
        evidence_chains: List[EvidenceChain],
        hallucination: Dict,
        language: str = "zh",
    ) -> str:
        """生成 Markdown 格式的溯源报告附录。"""
        if language == "zh":
            lines = [
                "## 证据链与可信度附录",
                "",
                f"本附录为报告中的关键结论自动建立了可追溯的证据链。共验证 {len(evidence_chains)} 条声明，"
                f"幻觉风险评分：**{hallucination.get('risk_score', 0.0):.1%}**。",
                "",
            ]
        else:
            lines = [
                "## Evidence Chain & Credibility Appendix",
                "",
                f"This appendix provides a traceable evidence chain for key claims. "
                f"Verified {len(evidence_chains)} claims; hallucination risk: **{hallucination.get('risk_score', 0.0):.1%}**.",
                "",
            ]

        zh = language == "zh"
        label_confidence = "置信度" if zh else "Confidence"
        label_verdict = "验证结论" if zh else "Verdict"
        label_support = "支持来源" if zh else "Supporting sources"
        label_refute = "反驳来源" if zh else "Refuting sources"
        label_domains = "来源域名" if zh else "Source domains"
        label_concerns = "风险提醒" if zh else "Risk reminders"
        label_snippets = "证据片段" if zh else "Evidence snippets"
        label_no_evidence = "未找到相关证据。" if zh else "No relevant evidence found."
        label_risk_marker = "幻觉风险标记" if zh else "Hallucination risk markers"

        for idx, chain in enumerate(evidence_chains, 1):
            loc_label = self._localize_label(chain.confidence_label, language)
            badge = self._badge(chain.confidence_label)
            lines.append(f"### {idx}. {badge} {chain.claim.text}")
            lines.append("")
            lines.append(
                f"- **{label_confidence}**: {chain.confidence_score}/100（{loc_label}）"
            )
            lines.append(f"- **{label_verdict}**: {chain.verdict.value}")
            lines.append(
                f"- **{label_support}**: {chain.supporting_count} | **{label_refute}**: {chain.refuting_count}"
            )
            if chain.unique_domains:
                lines.append(f"- **{label_domains}**: {', '.join(chain.unique_domains[:5])}")
            if chain.concerns:
                lines.append(f"- **{label_concerns}**: {'；'.join(chain.concerns)}")
            lines.append("")

            if chain.evidences:
                lines.append(f"**{label_snippets}**:")
                for ev in chain.evidences[:5]:
                    stance = _STANCE_LOCALE.get(ev.stance.value, {}).get(language, ev.stance.value)
                    lines.append(
                        f"> [{ev.source_index}] *{ev.title}* — {stance}（{label_confidence} {ev.relevance_score}/10）"
                    )
                    lines.append(f"> {ev.quote}")
                    lines.append(f"> {'来源' if zh else 'Source'}：<{ev.url}>")
                    lines.append("")
            else:
                lines.append(f"*{label_no_evidence}*")
                lines.append("")

        flagged = hallucination.get("flagged_sentences", [])
        if flagged:
            lines.append("---")
            lines.append(f"### {label_risk_marker}")
            lines.append("")
            for item in flagged[:10]:
                lines.append(f"- ⚠️ {item['reason']}：{item['sentence']}")
            lines.append("")

        return "\n".join(lines)

    def _localize_label(self, label: str, language: str) -> str:
        return _LABEL_LOCALE.get(label, {}).get(language, label)

    def _badge(self, label: str) -> str:
        mapping = {
            "已验证": "✅",
            "较可信": "🟢",
            "存在争议": "🟡",
            "未证实": "🟠",
            "被反驳": "🔴",
        }
        return mapping.get(label, "⚪")
