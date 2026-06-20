"""实时研究情报系统。

持续扫描全球学术源，发现与知识库主题相关的新突破，
生成个性化简报并主动推送。
"""

from intelligence.models import Alert, Article, Briefing, RelevanceScores
from intelligence.service import IntelligenceService

__all__ = [
    "Article",
    "Alert",
    "Briefing",
    "RelevanceScores",
    "IntelligenceService",
]
