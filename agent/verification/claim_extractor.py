"""从研究发现或报告中提取可验证声明。"""

import hashlib
import re
from typing import List

from agent.agents.base import BaseAgent
from agent.config import LLMConfig
from agent.research_state import ResearchState

from .models import Claim


class ClaimExtractor(BaseAgent):
    """提取可验证声明：优先从报告正文中抽取，失败时回退到 findings。"""

    name = "ClaimExtractor"

    def __init__(self, config: LLMConfig, progress_callback=None):
        super().__init__(config, progress_callback)

    def extract_claims(
        self,
        state: ResearchState,
        max_claims: int = 10,
        language: str = "zh",
    ) -> List[Claim]:
        """提取可验证声明。"""
        self._progress("正在提取可验证声明...")

        if state.report_body and len(state.report_body) > 50:
            claims = self._extract_from_report(state.report_body, max_claims, language)
        else:
            claims = []

        if len(claims) < max_claims:
            from_findings = self._extract_from_findings(state, max_claims - len(claims))
            seen = {c.text.strip().lower() for c in claims}
            for claim in from_findings:
                if claim.text.strip().lower() not in seen:
                    claims.append(claim)
                    seen.add(claim.text.strip().lower())

        self._progress(f"提取到 {len(claims)} 条可验证声明")
        return claims[:max_claims]

    def _extract_from_findings(
        self,
        state: ResearchState,
        max_claims: int,
    ) -> List[Claim]:
        """将关键发现作为声明。"""
        claims = []
        seen = set()
        for finding in state.findings:
            text = finding.strip()
            key = self._normalize(text)
            if not text or key in seen or len(text) < 10:
                continue
            seen.add(key)
            claims.append(
                Claim(
                    id=self._generate_id(text),
                    text=text,
                    context="",
                    source="finding",
                )
            )
            if len(claims) >= max_claims:
                break
        return claims

    def _extract_from_report(
        self,
        report_body: str,
        max_claims: int,
        language: str,
    ) -> List[Claim]:
        """使用 LLM 从报告正文中抽取事实性声明。"""
        system = (
            "You are a claim extraction assistant. Read the provided research report and "
            "extract factual claims that should be verified. Ignore generic background, "
            "opinions, or section headers. Return ONLY a JSON object with a 'claims' key "
            "containing a list of objects. Each object must have:\n"
            "- id: a short unique identifier (e.g., claim_1)\n"
            "- text: the factual claim to verify\n"
            "- context: the surrounding sentence or paragraph where the claim appears"
        )
        lang_hint = "Respond in Chinese." if language == "zh" else "Respond in English."
        user = (
            f"Report:\n{report_body[:6000]}\n\n"
            f"Extract up to {max_claims} factual claims. Return structured JSON. {lang_hint}"
        )

        try:
            content = self.complete(system, user, json_mode=True)
            data = self.parse_json(content, {"claims": []})
            raw_claims = data.get("claims", [])
        except Exception as exc:
            self._progress(f"LLM 声明提取失败，使用规则回退: {exc}")
            raw_claims = []

        claims = []
        seen = set()
        for item in raw_claims:
            if not isinstance(item, dict):
                continue
            text = str(item.get("text", "")).strip()
            if not text or len(text) < 10:
                continue
            key = self._normalize(text)
            if key in seen:
                continue
            seen.add(key)
            claims.append(
                Claim(
                    id=str(item.get("id", self._generate_id(text))),
                    text=text,
                    context=str(item.get("context", "")).strip(),
                    source="report",
                )
            )

        if not claims:
            # 规则回退：按句子切分，保留含事实性表达的句子
            claims = self._fallback_sentences(report_body, max_claims)

        return claims[:max_claims]

    def _fallback_sentences(self, report_body: str, max_claims: int) -> List[Claim]:
        """简单的句子级回退提取。"""
        sentences = re.split(r"(?<=[。！？.!?])\s+", report_body)
        claims = []
        seen = set()
        for sentence in sentences:
            text = sentence.strip()
            # 跳过标题、列表标记、过短句
            if text.startswith("#") or text.startswith("-") or len(text) < 15:
                continue
            # 优先保留含数字、年份、比例等事实性内容的句子
            if not re.search(r"\d|%|年|倍|增长|下降|达到|超过", text):
                continue
            key = self._normalize(text)
            if key in seen:
                continue
            seen.add(key)
            claims.append(
                Claim(
                    id=self._generate_id(text),
                    text=text,
                    context="",
                    source="report",
                )
            )
            if len(claims) >= max_claims:
                break
        return claims

    @staticmethod
    def _normalize(text: str) -> str:
        return " ".join(text.lower().split())

    @staticmethod
    def _generate_id(text: str) -> str:
        return hashlib.md5(text.encode("utf-8")).hexdigest()[:10]
