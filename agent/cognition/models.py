"""认知控制层数据模型。"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SubTask:
    """子任务。"""

    id: str
    description: str
    goal: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"  # pending / running / completed / failed
    result: Optional[str] = None
    sources_used: List[str] = field(default_factory=list)


@dataclass
class Plan:
    """研究计划。"""

    topic: str
    subtasks: List[SubTask]
    iteration: int = 0
    max_iterations: int = 3

    def pending_subtasks(self) -> List[SubTask]:
        return [s for s in self.subtasks if s.status == "pending"]

    def ready_subtasks(self) -> List[SubTask]:
        """返回依赖已全部完成的待执行子任务。"""
        completed_ids = {s.id for s in self.subtasks if s.status == "completed"}
        return [
            s
            for s in self.subtasks
            if s.status == "pending" and set(s.dependencies).issubset(completed_ids)
        ]

    def is_complete(self) -> bool:
        return all(s.status in ("completed", "failed") for s in self.subtasks)


@dataclass
class Reflection:
    """元认知反思结果。"""

    information_gaps: List[str] = field(default_factory=list)
    source_bias_notes: List[str] = field(default_factory=list)
    plan_deviation: str = ""
    suggested_queries: List[str] = field(default_factory=list)
    should_replan: bool = False
    reasoning: str = ""


@dataclass
class ExecutionTrace:
    """单条执行记录。"""

    subtask_id: str
    action: str
    input_summary: str
    output_summary: str
    timestamp: str


@dataclass
class WorkingMemory:
    """认知控制器的工作记忆。"""

    topic: str
    context: str = ""
    plan: Optional[Plan] = None
    reflections: List[Reflection] = field(default_factory=list)
    traces: List[ExecutionTrace] = field(default_factory=list)
    related_reports: List[Dict[str, Any]] = field(default_factory=list)

    def to_prompt_context(self) -> str:
        lines = [f"主题：{self.topic}"]
        if self.context:
            lines.append(f"背景上下文：{self.context}")
        if self.plan:
            lines.append("当前计划：")
            for st in self.plan.subtasks:
                lines.append(f"- [{st.status}] {st.id}: {st.description}")
        if self.reflections:
            lines.append("最新反思：")
            for r in self.reflections[-3:]:
                lines.append(f"- 缺口：{', '.join(r.information_gaps) or '无'}")
                if r.suggested_queries:
                    lines.append(f"  建议查询：{', '.join(r.suggested_queries)}")
        return "\n".join(lines)
