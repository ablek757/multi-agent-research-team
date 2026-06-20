from dataclasses import dataclass
from typing import List

from agent.config import SearchConfig


@dataclass
class SearchResult:
    title: str
    url: str
    snippet: str


class SearchEngine:
    def __init__(self, config: SearchConfig):
        self.config = config

    def search(self, query: str, num_results: int | None = None) -> List[SearchResult]:
        if self.config.backend == "duckduckgo":
            return self._search_duckduckgo(query, num_results or self.config.results_per_query)
        raise ValueError(f"Unsupported search backend: {self.config.backend}")

    def _search_duckduckgo(self, query: str, num_results: int) -> List[SearchResult]:
        try:
            from ddgs import DDGS
        except ImportError as exc:
            raise ImportError(
                "ddgs is required. Install with: pip install ddgs"
            ) from exc

        results: List[SearchResult] = []
        errors = []
        # Try html backend first (more stable), then lite, then auto
        for backend in ("html", "lite", "auto"):
            try:
                with DDGS() as ddgs:
                    raw_results = ddgs.text(
                        query,
                        region=self.config.region,
                        safesearch=self.config.safe_search,
                        backend=backend,
                        max_results=num_results,
                    )
                    for r in raw_results:
                        results.append(
                            SearchResult(
                                title=r.get("title", ""),
                                url=r.get("href", ""),
                                snippet=r.get("body", ""),
                            )
                        )
                    if results:
                        return results
            except Exception as exc:
                errors.append(f"{backend}: {exc}")

        raise RuntimeError(
            f"DuckDuckGo search failed for query '{query}'. Tried backends: {', '.join(errors)}"
        )
