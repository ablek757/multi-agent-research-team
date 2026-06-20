"""可信验证与溯源系统的数据模型。"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class EvidenceStance(str, Enum):
    """证据对声明的立场。"""

    SUPPORT = "support"
    REFUTE = "refute"
    NEUTRAL = "neutral"


class VerificationVerdict(str, Enum):
    """验证结论。"""

    VERIFIED = "verified"          # 已验证
    PLAUSIBLE = "plausible"        # 较可信
    CONTESTED = "contested"        # 存在争议
    UNSUPPORTED = "unsupported"    # 未证实
    REFUTED = "refuted"            # 被反驳


@dataclass
class Claim:
    """一个需要验证的声明。"""

    id: str
    text: str
    context: str = ""              # 声明在原文中的上下文/段落
    source: str = "finding"        # 来源：finding / report


@dataclass
class Evidence:
    """支持或反驳某个声明的证据片段。"""

    source_index: int
    url: str
    title: str
    quote: str                     # 来源中的关键引用
    context: str = ""              # 引用上下文
    stance: EvidenceStance = EvidenceStance.SUPPORT
    relevance_score: int = 5       # 1-10
    domain: str = ""               # 来源域名
    is_direct_quote: bool = False  # 是否包含直接可溯源的原文引用


@dataclass
class EvidenceChain:
    """某个声明的完整证据链。"""

    claim: Claim
    evidences: List[Evidence] = field(default_factory=list)
    verdict: VerificationVerdict = VerificationVerdict.UNSUPPORTED
    confidence_score: int = 0      # 0-100
    confidence_label: str = "未证实"
    supporting_count: int = 0
    refuting_count: int = 0
    unique_domains: List[str] = field(default_factory=list)
    assessment: str = ""           # 评估说明
    concerns: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim.id,
            "claim_text": self.claim.text,
            "claim_context": self.claim.context,
            "verdict": self.verdict.value,
            "confidence_score": self.confidence_score,
            "confidence_label": self.confidence_label,
            "supporting_count": self.supporting_count,
            "refuting_count": self.refuting_count,
            "unique_domains": self.unique_domains,
            "assessment": self.assessment,
            "concerns": self.concerns,
            "evidences": [
                {
                    "source_index": e.source_index,
                    "url": e.url,
                    "title": e.title,
                    "quote": e.quote,
                    "context": e.context,
                    "stance": e.stance.value,
                    "relevance_score": e.relevance_score,
                    "domain": e.domain,
                    "is_direct_quote": e.is_direct_quote,
                }
                for e in self.evidences
            ],
        }
