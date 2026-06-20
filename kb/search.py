"""全文检索与倒排索引。"""

import re
from collections import defaultdict
from typing import Dict, List

from kb.models import Report


class KnowledgeSearch:
    """基于简单倒排索引的全文搜索。"""

    def __init__(self):
        self.inverted_index: Dict[str, Dict[str, float]] = defaultdict(dict)

    def _tokenize(self, text: str) -> List[str]:
        # 中文按字，英文按词
        text = text.lower()
        # 提取英文单词
        words = re.findall(r"[a-z0-9]+", text)
        # 提取中文字符
        chars = re.findall(r"[\u4e00-\u9fff]", text)
        return words + chars

    def index_report(self, report: Report):
        fields = {
            "title": report.title,
            "topic": report.topic,
            "content": report.content,
            "findings": " ".join(f.text for f in report.findings),
            "entities": " ".join(e.name for e in report.entities),
            "topics": " ".join(t.name for t in report.topics),
        }

        weights = {
            "title": 5.0,
            "topic": 4.0,
            "entities": 3.0,
            "topics": 3.0,
            "findings": 2.0,
            "content": 1.0,
        }

        for field, text in fields.items():
            for token in self._tokenize(text):
                self.inverted_index[token][report.id] = (
                    self.inverted_index[token].get(report.id, 0) + weights[field]
                )

    def search(self, query: str, top_k: int = 20) -> List[Dict[str, any]]:
        tokens = self._tokenize(query)
        if not tokens:
            return []

        scores: Dict[str, float] = defaultdict(float)
        for token in tokens:
            for report_id, weight in self.inverted_index.get(token, {}).items():
                scores[report_id] += weight

        results = [
            {"report_id": report_id, "score": score}
            for report_id, score in scores.items()
        ]
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def clear(self):
        self.inverted_index.clear()
