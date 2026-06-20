"""认知控制器：动态任务规划、执行、反思与重规划。"""

import logging
from datetime import datetime
from typing import Callable, List, Optional

from agent.cognition.meta_critic import MetaCritic
from agent.cognition.models import ExecutionTrace, Plan, SubTask, WorkingMemory
from agent.cognition.planner import TaskPlanner
from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import TeamOrchestrator
from agent.research_state import ResearchState
from agent.tools import ToolRegistry

logger = logging.getLogger(__name__)


class CognitiveController:
    """认知增强型研究控制器。

    通过任务分解、子任务执行、元认知反思和重规划，提升研究深度与可控性。
    """

    def __init__(
        self,
        config: Config,
        llm: LLMClient,
        progress_callback: Callable[[str], None] = None,
        kb_store=None,
        tool_registry: Optional[ToolRegistry] = None,
    ):
        self.config = config
        self.llm = llm
        self.progress_callback = progress_callback or (lambda msg: None)
        self.kb_store = kb_store
        self.tool_registry = tool_registry

        self.planner = TaskPlanner(llm, max_subtasks=config.cognition.max_subtasks)
        self.critic = MetaCritic(llm)

    def run(self, topic: str) -> ResearchState:
        """执行认知增强研究并返回最终研究状态。"""
        self._progress(f"[认知控制] 启动主题研究: {topic}")

        # 1. 加载相关历史研究
        related_summaries: List[str] = []
        if self.kb_store is not None:
            try:
                related = self.kb_store.semantic_search(topic, top_k=3)
                related_summaries = [
                    f"{r['report'].get('title', '')}: {r['report'].get('summary', '')[:200]}"
                    for r in related
                ]
                self._progress(f"[认知控制] 找到 {len(related_summaries)} 份相关历史研究")
            except Exception as exc:
                logger.warning("加载相关历史研究失败: %s", exc)

        # 2. 任务分解
        context = ""
        if related_summaries:
            context = "可参考以下历史研究摘要：\n" + "\n".join(related_summaries)
        plan = self.planner.decompose(
            topic=topic,
            context=context,
            language=self.config.research.language,
        )
        self._progress(f"[认知控制] 生成 {len(plan.subtasks)} 个子任务")

        memory = WorkingMemory(topic=topic, plan=plan, related_reports=[])

        # 3. 执行循环
        main_state = ResearchState()
        max_replan = self.config.cognition.max_replan_iterations
        replan_count = 0

        while not plan.is_complete():
            ready = plan.ready_subtasks()
            if not ready:
                # 无就绪子任务但计划未完成，说明有循环依赖或未失败子任务卡住
                pending = plan.pending_subtasks()
                if pending:
                    ready = [pending[0]]
                else:
                    break

            for subtask in ready:
                self._execute_subtask(subtask, topic, main_state, memory)

            # 反思
            reflection = self.critic.reflect(
                topic=topic,
                state=main_state,
                plan_summary=memory.to_prompt_context(),
                language=self.config.research.language,
            )
            memory.reflections.append(reflection)
            self._progress(
                f"[认知控制] 反思: {reflection.reasoning[:120]}..."
            )

            # 重规划
            if reflection.should_replan and replan_count < max_replan:
                plan = self.planner.replan(
                    plan=plan,
                    reflection_reasoning=reflection.reasoning,
                    language=self.config.research.language,
                )
                memory.plan = plan
                replan_count += 1
                self._progress(f"[认知控制] 执行第 {replan_count} 次重规划")

            # 若反思提供了建议查询，补充进主状态以便下一轮搜索
            if reflection.suggested_queries:
                main_state.open_questions.extend(reflection.suggested_queries)

        # 4. 综合最终报告
        self._progress("[认知控制] 综合各子任务结果生成最终报告")
        final_state = self._synthesize(topic, main_state, memory)

        # 5. 质量评估
        try:
            from agent.evaluation import ReportEvaluator
            evaluator = ReportEvaluator(self.config)
            metrics = evaluator.evaluate(topic, final_state, final_state.report_body)
            final_state.metrics = metrics.to_dict()
            self._progress(f"[认知控制] 报告综合质量评分: {metrics.overall_score:.2f}")
        except Exception as exc:
            logger.warning("质量评估失败: %s", exc)

        return final_state

    def _execute_subtask(
        self,
        subtask: SubTask,
        topic: str,
        main_state: ResearchState,
        memory: WorkingMemory,
    ):
        self._progress(f"[子任务 {subtask.id}] {subtask.description}")
        subtask.status = "running"

        # 构建子任务主题：继承主主题 + 子任务目标
        subtopic = f"{topic} - {subtask.goal or subtask.description}"

        # 运行现有研究团队流水线
        orchestrator = TeamOrchestrator(
            config=self.config,
            progress_callback=self.progress_callback,
        )
        sub_state = orchestrator.run(subtopic)

        # 合并子结果到主状态
        self._merge_state(main_state, sub_state, subtask)

        subtask.status = "completed"
        subtask.result = sub_state.report_body[:500]
        subtask.sources_used = [s.url for s in sub_state.sources]

        memory.traces.append(
            ExecutionTrace(
                subtask_id=subtask.id,
                action="team_orchestrator",
                input_summary=subtopic,
                output_summary=f"sources={len(sub_state.sources)}, findings={len(sub_state.findings)}",
                timestamp=datetime.now().isoformat(),
            )
        )

    def _merge_state(self, main: ResearchState, sub: ResearchState, subtask: SubTask):
        # 合并来源（去重 URL）
        existing_urls = {s.url for s in main.sources}
        for s in sub.sources:
            if s.url not in existing_urls:
                s.index = len(main.sources) + 1
                main.sources.append(s)
                existing_urls.add(s.url)

        main.summaries.extend(sub.summaries)
        main.findings.extend(sub.findings)
        main.entities.extend(sub.entities)
        main.themes.extend(sub.themes)
        main.connections.extend(sub.connections)
        main.contradictions.extend(sub.contradictions)
        main.gaps.extend(sub.gaps)
        main.open_questions.extend(sub.open_questions)
        main.verification_results.extend(sub.verification_results)
        main.editor_feedback.extend(sub.editor_feedback)
        main.revisions.extend(sub.revisions)

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

    def _synthesize(self, topic: str, main_state: ResearchState, memory: WorkingMemory) -> ResearchState:
        """基于各子任务结果生成综合报告。"""
        # 使用现有 Writer 生成综合报告
        from agent.agents import Writer

        style_profile = self._load_style_profile()
        writer = Writer(self.config.llm, self.progress_callback)
        report_body = writer.write(
            topic,
            main_state,
            self.config.research.language,
            style_profile=style_profile,
        )

        # 若启用编辑，执行审稿修订
        if self.config.team.enable_editor and self.config.team.review_rounds > 0:
            from agent.agents import Editor

            editor = Editor(self.config.llm, self.progress_callback)
            for round_num in range(1, self.config.team.review_rounds + 1):
                feedback = editor.review(topic, report_body, main_state, self.config.research.language)
                main_state.editor_feedback.append(feedback)
                report_body = writer.revise(
                    topic,
                    report_body,
                    feedback,
                    main_state,
                    self.config.research.language,
                    style_profile=style_profile,
                )
                main_state.revisions.append(
                    {
                        "round": round_num,
                        "feedback": feedback,
                        "after": report_body,
                    }
                )

        main_state.report_body = report_body
        return main_state

    def _progress(self, message: str):
        logger.info(message)
        self.progress_callback(message)
