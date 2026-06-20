import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, List

from agent.config import Config
from agent.fetcher import WebPage, fetch_page
from agent.llm import LLMClient
from agent.research_state import PageSummary, ResearchState
from agent.search import SearchEngine, SearchResult

logger = logging.getLogger(__name__)


class ResearchOrchestrator:
    def __init__(self, config: Config, progress_callback: Callable[[str], None] | None = None):
        self.config = config
        self.llm = LLMClient(config.llm)
        self.search = SearchEngine(config.search)
        self.state = ResearchState()
        self.progress_callback = progress_callback or (lambda msg: None)

    def run(self, topic: str) -> ResearchState:
        self._progress(f"开始研究主题: {topic}")

        # Initial queries
        queries = self.llm.generate_search_queries(
            topic,
            self.config.research.queries_per_round,
            self.config.research.language,
        )
        self._progress(f"生成初始查询: {queries}")

        for round_num in range(1, self.config.research.depth + 1):
            self._progress(f"===== 第 {round_num}/{self.config.research.depth} 轮搜索 =====")
            self._research_round(topic, queries, round_num)

            if round_num < self.config.research.depth:
                queries = self.llm.identify_gaps(
                    topic=topic,
                    findings=self.state.findings,
                    entities=self.state.entities,
                    open_questions=self.state.open_questions,
                    count=self.config.research.queries_per_round,
                    language=self.config.research.language,
                )
                self._progress(f"下一轮查询: {queries}")

        self._progress("研究完成，准备生成报告...")
        return self.state

    def _research_round(self, topic: str, queries: List[str], round_num: int):
        all_results: List[SearchResult] = []
        for query in queries:
            try:
                results = self.search.search(query)
                self._progress(f"查询 '{query}' 返回 {len(results)} 条结果")
                all_results.extend(results)
            except Exception as exc:
                logger.warning("Search failed for query '%s': %s", query, exc)
                self._progress(f"搜索失败: {query} -> {exc}")

        # Deduplicate and filter already visited
        unique_results: List[SearchResult] = []
        seen_urls = set()
        for r in all_results:
            if not r.url or r.url in seen_urls or r.url in self.state.visited_urls:
                continue
            seen_urls.add(r.url)
            unique_results.append(r)

        to_fetch = unique_results[: self.config.search.top_k_to_fetch * len(queries)]
        self._progress(f"本轮将抓取 {len(to_fetch)} 个新页面")

        # Preserve search result titles in case page extraction fails to get one
        url_to_search_title = {r.url: r.title for r in to_fetch}

        # Fetch concurrently
        fetched = self._fetch_pages(to_fetch)

        for page in fetched:
            if page.error or not page.content.strip():
                continue
            title = page.title or url_to_search_title.get(page.url, "")
            try:
                extracted = self.llm.summarize_page(
                    title=title,
                    url=page.url,
                    content=page.content,
                    topic=topic,
                    language=self.config.research.language,
                )
                source_index = self.state.add_source(
                    title=title or extracted.get("title", ""),
                    url=page.url,
                    snippet="",
                )
                summary = PageSummary(
                    source_index=source_index,
                    url=page.url,
                    title=title or extracted.get("title", ""),
                    summary=extracted.get("summary", ""),
                    key_findings=extracted.get("key_findings", []),
                    entities=extracted.get("entities", []),
                    open_questions=extracted.get("open_questions", []),
                    relevance_score=extracted.get("relevance_score", 5),
                )
                self.state.add_summary(summary)
                self._progress(
                    f"已总结 [{source_index}] {summary.title[:60]}... "
                    f"(相关度: {summary.relevance_score})"
                )
            except Exception as exc:
                logger.warning("Failed to summarize %s: %s", page.url, exc)
                self._progress(f"总结失败: {page.url} -> {exc}")

    def _fetch_pages(self, results: List[SearchResult]) -> List[WebPage]:
        pages: List[WebPage] = []
        max_workers = min(self.config.search.max_workers, len(results))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(
                    fetch_page,
                    r.url,
                    max_length=self.config.research.max_content_length,
                ): r
                for r in results
            }
            for future in as_completed(future_to_url):
                try:
                    page = future.result()
                    pages.append(page)
                except Exception as exc:
                    r = future_to_url[future]
                    logger.warning("Exception fetching %s: %s", r.url, exc)
        return pages

    def _progress(self, message: str):
        logger.info(message)
        self.progress_callback(message)
