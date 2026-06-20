import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

from agent.agents.base import BaseAgent
from agent.config import Config
from agent.fetcher import WebPage, fetch_page
from agent.research_state import PageSummary, ResearchState
from agent.search import SearchEngine, SearchResult

logger = logging.getLogger(__name__)


class Researcher(BaseAgent):
    """研究员：执行搜索、抓取网页并提取结构化信息。"""

    name = "Researcher"

    def __init__(
        self,
        config: Config,
        progress_callback=None,
    ):
        super().__init__(config.llm, progress_callback)
        self.config = config
        self.search = SearchEngine(config.search)

    def research(
        self,
        topic: str,
        queries: List[str],
        state: ResearchState,
    ) -> None:
        """根据查询列表收集信息并更新研究状态。"""
        self._progress(f"开始执行 {len(queries)} 个查询...")
        all_results: List[SearchResult] = []
        for query in queries:
            try:
                results = self.search.search(query)
                self._progress(f"查询 '{query}' 返回 {len(results)} 条结果")
                all_results.extend(results)
            except Exception as exc:
                logger.warning("Search failed for query '%s': %s", query, exc)
                self._progress(f"搜索失败: {query} -> {exc}")

        unique_results = self._dedup_results(all_results, state)
        top_k = self.config.search.top_k_to_fetch * len(queries)
        to_fetch = unique_results[:top_k]
        self._progress(f"本轮将抓取 {len(to_fetch)} 个新页面")

        if not to_fetch:
            return

        url_to_search_title = {r.url: r.title for r in to_fetch}
        fetched = self._fetch_pages(to_fetch)

        for page in fetched:
            if page.error or not page.content.strip():
                continue
            title = page.title or url_to_search_title.get(page.url, "")
            try:
                extracted = self._summarize_page(title, page.url, page.content, topic)
                source_index = state.add_source(
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
                state.add_summary(summary)
                self._progress(
                    f"已总结 [{source_index}] {summary.title[:60]}... "
                    f"(相关度: {summary.relevance_score})"
                )
            except Exception as exc:
                logger.warning("Failed to summarize %s: %s", page.url, exc)
                self._progress(f"总结失败: {page.url} -> {exc}")

    def _dedup_results(
        self,
        results: List[SearchResult],
        state: ResearchState,
    ) -> List[SearchResult]:
        seen_urls = set()
        unique: List[SearchResult] = []
        for r in results:
            if not r.url or r.url in seen_urls or r.url in state.visited_urls:
                continue
            seen_urls.add(r.url)
            unique.append(r)
        return unique

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

    def _summarize_page(
        self,
        title: str,
        url: str,
        content: str,
        topic: str,
    ) -> dict:
        system = (
            "You are an expert information extractor. Read the provided web page content "
            "and return a JSON object with these keys:\n"
            "- summary: a concise summary (2-4 sentences)\n"
            "- key_findings: a list of key factual claims or findings relevant to the topic\n"
            "- entities: a list of important people, organizations, technologies, or concepts\n"
            "- open_questions: a list of questions this page raises or leaves unanswered\n"
            "- relevance_score: integer 1-10 indicating relevance to the topic\n"
            "Return ONLY valid JSON."
        )
        lang_hint = (
            "Respond in Chinese." if self.config.research.language == "zh" else "Respond in English."
        )
        user = (
            f"Topic: {topic}\n"
            f"Page title: {title}\n"
            f"URL: {url}\n\n"
            f"Content:\n{content[:8000]}\n\n{lang_hint}"
        )
        content = self.complete(system, user, json_mode=True)
        try:
            return self.parse_json(content)
        except Exception:
            return {
                "summary": content,
                "key_findings": [],
                "entities": [],
                "open_questions": [],
                "relevance_score": 5,
            }
