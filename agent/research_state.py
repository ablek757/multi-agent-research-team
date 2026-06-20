import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set


@dataclass
class Source:
    index: int
    title: str
    url: str
    snippet: str = ""


@dataclass
class PageSummary:
    source_index: int
    url: str
    title: str
    summary: str
    key_findings: List[str] = field(default_factory=list)
    entities: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    relevance_score: int = 5


@dataclass
class VerificationResult:
    claim: str
    sources: List[str] = field(default_factory=list)
    credibility_score: int = 5
    assessment: str = ""
    concerns: List[str] = field(default_factory=list)


class ResearchState:
    def __init__(self):
        self.sources: List[Source] = []
        self.summaries: List[PageSummary] = []
        self.visited_urls: Set[str] = set()
        self.url_to_index: Dict[str, int] = {}
        self.findings: List[str] = []
        self.entities: List[str] = []
        self.open_questions: List[str] = []
        self.findings_hashes: Set[str] = set()
        self.entities_lower: Set[str] = set()

        # Multi-agent collaboration enriched state
        self.themes: List[str] = []
        self.connections: List[Dict[str, Any]] = []
        self.contradictions: List[Dict[str, Any]] = []
        self.gaps: List[str] = []
        self.verification_results: List[VerificationResult] = []
        self.editor_feedback: List[str] = []
        self.revisions: List[Dict[str, Any]] = []
        self.report_body: str = ""

    def add_source(self, title: str, url: str, snippet: str = "") -> int:
        if url in self.url_to_index:
            return self.url_to_index[url]
        index = len(self.sources) + 1
        source = Source(index=index, title=title, url=url, snippet=snippet)
        self.sources.append(source)
        self.url_to_index[url] = index
        return index

    def add_summary(self, summary: PageSummary):
        self.summaries.append(summary)
        self.visited_urls.add(summary.url)

        for finding in summary.key_findings:
            h = self._hash(finding)
            if h not in self.findings_hashes:
                self.findings_hashes.add(h)
                self.findings.append(finding)

        for entity in summary.entities:
            key = entity.lower().strip()
            if key and key not in self.entities_lower:
                self.entities_lower.add(key)
                self.entities.append(entity)

        for question in summary.open_questions:
            q = question.strip()
            if q and q not in self.open_questions:
                self.open_questions.append(q)

    def _hash(self, text: str) -> str:
        normalized = " ".join(text.lower().split())
        return hashlib.md5(normalized.encode("utf-8")).hexdigest()

    def get_source_by_url(self, url: str) -> Source | None:
        index = self.url_to_index.get(url)
        if index is None:
            return None
        return self.sources[index - 1]

    def to_dict(self) -> Dict:
        return {
            "sources": [
                {"index": s.index, "title": s.title, "url": s.url, "snippet": s.snippet}
                for s in self.sources
            ],
            "summaries": [
                {
                    "source_index": ps.source_index,
                    "url": ps.url,
                    "title": ps.title,
                    "summary": ps.summary,
                    "key_findings": ps.key_findings,
                    "entities": ps.entities,
                    "open_questions": ps.open_questions,
                    "relevance_score": ps.relevance_score,
                }
                for ps in self.summaries
            ],
            "findings": self.findings,
            "entities": self.entities,
            "open_questions": self.open_questions,
            "themes": self.themes,
            "connections": self.connections,
            "contradictions": self.contradictions,
            "gaps": self.gaps,
            "verification_results": [
                {
                    "claim": v.claim,
                    "sources": v.sources,
                    "credibility_score": v.credibility_score,
                    "assessment": v.assessment,
                    "concerns": v.concerns,
                }
                for v in self.verification_results
            ],
            "editor_feedback": self.editor_feedback,
            "revisions": self.revisions,
        }
