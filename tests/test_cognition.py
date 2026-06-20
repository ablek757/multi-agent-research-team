"""认知控制层测试。"""

from agent.cognition.models import Plan, SubTask
from agent.cognition.planner import TaskPlanner


class FakeLLMClient:
    """简单的伪 LLM 客户端。"""

    def __init__(self, responses=None):
        self.responses = responses or []
        self.call_count = 0

    def complete(self, system: str, user: str, json_mode: bool = False) -> str:
        idx = self.call_count % len(self.responses) if self.responses else 0
        self.call_count += 1
        return self.responses[idx]


def test_task_planner_decompose():
    response = """```json
[
  {"id": "t1", "description": "调研背景", "goal": "收集背景资料", "dependencies": []},
  {"id": "t2", "description": "分析现状", "goal": "总结当前进展", "dependencies": ["t1"]}
]
```"""
    planner = TaskPlanner(FakeLLMClient([response]), max_subtasks=3)
    plan = planner.decompose("量子计算", language="zh")
    assert isinstance(plan, Plan)
    assert len(plan.subtasks) == 2
    assert plan.subtasks[0].id == "t1"
    assert plan.subtasks[1].dependencies == ["t1"]


def test_plan_ready_subtasks():
    tasks = [
        SubTask(id="t1", description="a", goal="a"),
        SubTask(id="t2", description="b", goal="b", dependencies=["t1"]),
    ]
    plan = Plan(topic="x", subtasks=tasks)
    assert len(plan.ready_subtasks()) == 1
    tasks[0].status = "completed"
    assert len(plan.ready_subtasks()) == 1
    assert plan.ready_subtasks()[0].id == "t2"


def test_plan_is_complete():
    tasks = [
        SubTask(id="t1", description="a", goal="a", status="completed"),
        SubTask(id="t2", description="b", goal="b", status="completed"),
    ]
    plan = Plan(topic="x", subtasks=tasks)
    assert plan.is_complete()
