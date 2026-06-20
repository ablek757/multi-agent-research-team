import logging
from typing import Any, Callable, Dict, Optional

from agent.agents import Analyst, Editor, FactChecker, Researcher, SearchPlanner, Writer
from agent.agents.traceability_auditor import TraceabilityAuditor
from agent.config import Config
from agent.research_state import ResearchState
from agent.workbench.trace_models import TraceEventType

logger = logging.getLogger(__name__)

TraceCallback = Callable[[TraceEventType, Dict[str, Any], Optional[str], Optional[str], Optional[str]], None]


class TeamOrchestrator:
    """多 Agent 研究团队协调器。

    调度 SearchPlanner、Researcher、Analyst、FactChecker、Writer、Editor
    等角色，通过迭代搜索、分析、核查、撰稿与审稿，输出深度研究报告。
    当 cognition.enabled 为 true 时，每轮会调用 MetaCritic 进行反思。
    """

    def __init__(
        self,
        config: Config,
        progress_callback: Callable[[str], None] | None = None,
        trace_callback: TraceCallback | None = None,
    ):
        self.config = config
        self.progress_callback = progress_callback or (lambda msg: None)
        self.trace_callback = trace_callback
        self.state = ResearchState()
        self._current_node_id: Optional[str] = None

        self.search_planner = SearchPlanner(config.llm, progress_callback)
        self.researcher = Researcher(config, progress_callback)
        self.analyst = Analyst(config.llm, progress_callback)
        self.fact_checker = FactChecker(config.llm, progress_callback)
        self.writer = Writer(config.llm, progress_callback)
        self.editor = Editor(config.llm, progress_callback)
        self.traceability_auditor = TraceabilityAuditor(
            llm_config=config.llm,
            verification_config=config.verification,
            progress_callback=progress_callback,
        )
        self._meta_critic: Optional = None

    def _get_meta_critic(self):
        if self._meta_critic is None and self.config.cognition.enabled:
            from agent.cognition.meta_critic import MetaCritic
            self._meta_critic = MetaCritic(self.config.llm)
        return self._meta_critic

    def run(self, topic: str) -> ResearchState:
        self._progress(f"开始多 Agent 协作研究主题: {topic}")
        self._current_node_id = self._emit(
            TraceEventType.SESSION_STARTED,
            payload={"topic": topic, "mode": "team_orchestrator"},
        )

        max_iterations = self._max_research_iterations()
        queries = self.search_planner.plan_queries(
            topic,
            self.state,
            self.config.research.queries_per_round,
            self.config.research.language,
        )
        self._emit(
            TraceEventType.SEARCH_PLANNED,
            payload={"queries": queries, "iteration": 0},
        )

        for iteration in range(1, max_iterations + 1):
            self._progress(f"===== 第 {iteration}/{max_iterations} 轮研究 =====")
            iter_node = self._emit(
                TraceEventType.AGENT_ACTION,
                payload={"label": f"第 {iteration}/{max_iterations} 轮研究", "iteration": iteration},
            )
            self._research_iteration(topic, queries, iteration, parent_id=iter_node)

            # 认知增强：元认知反思
            if self.config.cognition.enabled:
                self._reflect(topic, iteration, parent_id=iter_node)

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
                self._emit(
                    TraceEventType.SEARCH_PLANNED,
                    payload={"queries": queries, "iteration": iteration},
                    parent_id=iter_node,
                )

        report_body = self._write_and_revise(topic)
        self.state.report_body = report_body

        # 可信验证与溯源审计
        if self.config.verification.enabled:
            try:
                self.traceability_auditor.audit(
                    topic=topic,
                    state=self.state,
                    language=self.config.research.language,
                )
                if self.config.verification.enable_auto_revision:
                    report_body = self.traceability_auditor.maybe_revise(
                        topic=topic,
                        state=self.state,
                        language=self.config.research.language,
                        style_profile=self._load_style_profile(),
                    )
                    self.state.report_body = report_body
            except Exception as exc:
                logger.warning("可信验证与溯源审计失败: %s", exc)

        # 质量评估
        try:
            from agent.evaluation import ReportEvaluator
            evaluator = ReportEvaluator(self.config)
            metrics = evaluator.evaluate(topic, self.state, report_body)
            self.state.metrics = metrics.to_dict()
            self._progress(f"报告综合质量评分: {metrics.overall_score:.2f}")
        except Exception as exc:
            logger.warning("质量评估失败: %s", exc)

        self._emit(
            TraceEventType.REPORT_GENERATED,
            payload={
                "sources": len(self.state.sources),
                "findings": len(self.state.findings),
                "metrics": self.state.metrics,
            },
        )
        self._progress("多 Agent 协作研究完成")
        return self.state

    def _research_iteration(self, topic: str, queries: list, iteration: int, parent_id: Optional[str] = None):
        before_sources = len(self.state.sources)
        before_findings = len(self.state.findings)

        search_node = self._emit(
            TraceEventType.SEARCH_EXECUTED,
            payload={"queries": queries, "iteration": iteration},
            parent_id=parent_id,
            agent="Researcher",
        )
        self.researcher.research(topic, queries, self.state)

        # 为新增的来源和发现发射事件
        for summary in self.state.summaries[before_sources:]:
            self._emit(
                TraceEventType.SOURCE_ADDED,
                payload={
                    "url": summary.url,
                    "title": summary.title,
                    "source_index": summary.source_index,
                    "summary": summary.summary[:200],
                },
                parent_id=search_node,
                agent="Researcher",
            )
            for finding in summary.key_findings:
                self._emit(
                    TraceEventType.FINDING_EXTRACTED,
                    payload={"finding": finding, "source_url": summary.url},
                    parent_id=search_node,
                    agent="Researcher",
                )

        if not self.state.summaries:
            self._progress("本轮未收集到有效信息，跳过分析与核查")
            return

        self._emit(
            TraceEventType.AGENT_ACTION,
            payload={"label": "Analyst 综合分析", "sources": len(self.state.sources)},
            parent_id=parent_id,
            agent="Analyst",
        )
        self.analyst.analyze(topic, self.state, self.config.research.language)

        if self.config.team.enable_fact_checker:
            self._emit(
                TraceEventType.AGENT_ACTION,
                payload={"label": "FactChecker 事实核查"},
                parent_id=parent_id,
                agent="FactChecker",
            )
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
        style_profile = self._load_style_profile()
        write_node = self._emit(
            TraceEventType.SYNTHESIS_STARTED,
            payload={"label": "Writer 撰写初稿"},
            agent="Writer",
        )
        report_body = self.writer.write(
            topic,
            self.state,
            self.config.research.language,
            style_profile=style_profile,
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
            self._emit(
                TraceEventType.AGENT_ACTION,
                payload={"label": f"Editor 第 {round_num} 轮审稿", "feedback": feedback[:200]},
                parent_id=write_node,
                agent="Editor",
            )
            report_body = self.writer.revise(
                topic,
                report_body,
                feedback,
                self.state,
                self.config.research.language,
                style_profile=style_profile,
            )
            self.state.revisions[-1]["after"] = report_body

            # 若启用风格学习，从修订中学习
            if self.config.style.enabled and self.config.style.auto_learn_from_edits:
                try:
                    from agent.style import StyleLearner
                    learner = StyleLearner(self.config.style, self.config.llm)
                    learner.learn_from_feedback(report_body, feedback)
                except Exception as exc:
                    logger.warning("风格学习失败: %s", exc)

        return report_body

    def _load_style_profile(self):
        if not self.config.style.enabled:
            return None
        try:
            from agent.style import StyleLearner
            learner = StyleLearner(self.config.style)
            profile = learner.load_profile()
            if profile.sample_count >= self.config.style.min_samples:
                return profile
        except Exception as exc:
            logger.warning("加载用户风格画像失败: %s", exc)
        return None

    def _reflect(self, topic: str, iteration: int, parent_id: Optional[str] = None):
        """调用 MetaCritic 进行反思，并将建议查询纳入后续轮次。"""
        critic = self._get_meta_critic()
        if critic is None:
            return
        self._progress(f"===== 第 {iteration} 轮元认知反思 =====")
        reflection = critic.reflect(
            topic=topic,
            state=self.state,
            language=self.config.research.language,
        )
        self.state.reflections.append(
            {
                "iteration": iteration,
                "reasoning": reflection.reasoning,
                "information_gaps": reflection.information_gaps,
                "source_bias_notes": reflection.source_bias_notes,
                "suggested_queries": reflection.suggested_queries,
            }
        )
        self._emit(
            TraceEventType.REFLECTION,
            payload={
                "iteration": iteration,
                "reasoning": reflection.reasoning,
                "information_gaps": reflection.information_gaps,
                "source_bias_notes": reflection.source_bias_notes,
                "suggested_queries": reflection.suggested_queries,
            },
            parent_id=parent_id,
            agent="MetaCritic",
        )
        if reflection.suggested_queries:
            for q in reflection.suggested_queries:
                if q not in self.state.open_questions:
                    self.state.open_questions.append(q)
        self._progress(f"反思结论：{reflection.reasoning[:120]}...")

    def _max_research_iterations(self) -> int:
        return self.config.team.max_research_iterations or self.config.research.depth

    def _progress(self, message: str):
        logger.info(message)
        self.progress_callback(message)

    def _emit(
        self,
        event_type: TraceEventType,
        payload: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> Optional[str]:
        if self.trace_callback is None:
            return node_id
        self.trace_callback(
            event_type,
            payload or {},
            parent_id=parent_id or self._current_node_id,
            node_id=node_id,
            agent=agent,
        )
        return node_id


# 保留旧名称的兼容别名
ResearchOrchestrator = TeamOrchestrator
