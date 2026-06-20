import logging
from typing import Callable

from agent.agents import Analyst, Editor, FactChecker, Researcher, SearchPlanner, Writer
from agent.config import Config
from agent.research_state import ResearchState

logger = logging.getLogger(__name__)


class TeamOrchestrator:
    """多 Agent 研究团队协调器。

    调度 SearchPlanner、Researcher、Analyst、FactChecker、Writer、Editor
    等角色，通过迭代搜索、分析、核查、撰稿与审稿，输出深度研究报告。
    """

    def __init__(self, config: Config, progress_callback: Callable[[str], None] | None = None):
        self.config = config
        self.progress_callback = progress_callback or (lambda msg: None)
        self.state = ResearchState()

        self.search_planner = SearchPlanner(config.llm, progress_callback)
        self.researcher = Researcher(config, progress_callback)
        self.analyst = Analyst(config.llm, progress_callback)
        self.fact_checker = FactChecker(config.llm, progress_callback)
        self.writer = Writer(config.llm, progress_callback)
        self.editor = Editor(config.llm, progress_callback)

    def run(self, topic: str) -> ResearchState:
        self._progress(f"开始多 Agent 协作研究主题: {topic}")

        max_iterations = self._max_research_iterations()
        queries = self.search_planner.plan_queries(
            topic,
            self.state,
            self.config.research.queries_per_round,
            self.config.research.language,
        )

        for iteration in range(1, max_iterations + 1):
            self._progress(f"===== 第 {iteration}/{max_iterations} 轮研究 =====")
            self._research_iteration(topic, queries, iteration)

            if iteration < max_iterations:
                if not self._should_continue_research():
                    self._progress("当前信息已足够充分，提前结束研究阶段")
                    break
                queries = self.search_planner.plan_queries(
                    topic,
                    self.state,
                    self.config.research.queries_per_round,
                    self.config.research.language,
                )

        report_body = self._write_and_revise(topic)
        self.state.report_body = report_body
        self._progress("多 Agent 协作研究完成")
        return self.state

    def _research_iteration(self, topic: str, queries: list, iteration: int):
        self.researcher.research(topic, queries, self.state)

        if not self.state.summaries:
            self._progress("本轮未收集到有效信息，跳过分析与核查")
            return

        self.analyst.analyze(topic, self.state, self.config.research.language)

        if self.config.team.enable_fact_checker:
            self.fact_checker.verify(
                topic,
                self.state,
                self.config.research.language,
                max_claims=self.config.team.max_claims_to_verify,
            )

    def _should_continue_research(self) -> bool:
        """判断是否还需要继续搜索迭代。"""
        # 如果存在明确的信息缺口，继续搜索
        if self.state.gaps:
            return True

        # 如果关键发现可信度偏低，继续搜索以补充验证
        if self.config.team.enable_fact_checker and self.state.verification_results:
            low_credibility = any(
                v.credibility_score < self.config.team.min_credibility_threshold
                for v in self.state.verification_results
            )
            if low_credibility:
                return True

        # 如果收集到的来源较少，继续搜索
        if len(self.state.sources) < self.config.search.top_k_to_fetch:
            return True

        return False

    def _write_and_revise(self, topic: str) -> str:
        report_body = self.writer.write(
            topic,
            self.state,
            self.config.research.language,
        )

        rounds = self.config.team.review_rounds if self.config.team.enable_editor else 0
        for round_num in range(1, rounds + 1):
            self._progress(f"===== 第 {round_num}/{rounds} 轮审稿修订 =====")
            feedback = self.editor.review(
                topic,
                report_body,
                self.state,
                self.config.research.language,
            )
            self.state.editor_feedback.append(feedback)
            self.state.revisions.append(
                {
                    "round": round_num,
                    "feedback": feedback,
                    "before": report_body,
                }
            )
            report_body = self.writer.revise(
                topic,
                report_body,
                feedback,
                self.state,
                self.config.research.language,
            )
            self.state.revisions[-1]["after"] = report_body

        return report_body

    def _max_research_iterations(self) -> int:
        return self.config.team.max_research_iterations or self.config.research.depth

    def _progress(self, message: str):
        logger.info(message)
        self.progress_callback(message)


# 保留旧名称的兼容别名
ResearchOrchestrator = TeamOrchestrator
