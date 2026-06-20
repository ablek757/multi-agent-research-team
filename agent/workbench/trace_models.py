"""认知探索工作台事件模型。"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class TraceEventType(str, Enum):
    """研究过程事件类型。"""

    SESSION_STARTED = "session_started"
    PLAN_CREATED = "plan_created"
    SUBTASK_STARTED = "subtask_started"
    SUBTASK_COMPLETED = "subtask_completed"
    SUBTASK_FAILED = "subtask_failed"
    SEARCH_PLANNED = "search_planned"
    SEARCH_EXECUTED = "search_executed"
    SOURCE_ADDED = "source_added"
    FINDING_EXTRACTED = "finding_extracted"
    AGENT_ACTION = "agent_action"
    REFLECTION = "reflection"
    REPLAN = "replan"
    CHECKPOINT = "checkpoint"
    INTERVENTION = "intervention"
    FORK = "fork"
    SYNTHESIS_STARTED = "synthesis_started"
    REPORT_GENERATED = "report_generated"
    SESSION_COMPLETED = "session_completed"
    SESSION_FAILED = "session_failed"


@dataclass
class TraceEvent:
    """单条研究过程事件。"""

    id: str
    session_id: str
    type: TraceEventType
    timestamp: str
    payload: Dict[str, Any] = field(default_factory=dict)
    parent_id: Optional[str] = None
    node_id: Optional[str] = None
    agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "session_id": self.session_id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "parent_id": self.parent_id,
            "node_id": self.node_id,
            "agent": self.agent,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TraceEvent":
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            type=TraceEventType(data["type"]),
            timestamp=data["timestamp"],
            payload=data.get("payload", {}),
            parent_id=data.get("parent_id"),
            node_id=data.get("node_id"),
            agent=data.get("agent"),
        )

    @classmethod
    def create(
        cls,
        session_id: str,
        type: TraceEventType,
        payload: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> "TraceEvent":
        import uuid

        return cls(
            id=f"evt_{uuid.uuid4().hex[:12]}",
            session_id=session_id,
            type=type,
            timestamp=datetime.now().isoformat(),
            payload=payload or {},
            parent_id=parent_id,
            node_id=node_id or f"node_{uuid.uuid4().hex[:12]}",
            agent=agent,
        )
