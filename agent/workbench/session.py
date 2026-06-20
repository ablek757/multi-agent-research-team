"""认知探索工作台会话：状态、事件、检查点与分叉管理。"""

import json
import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent.research_state import ResearchState
from agent.workbench.trace_emitter import TraceEmitter
from agent.workbench.trace_models import TraceEvent, TraceEventType

logger = logging.getLogger(__name__)


@dataclass
class WorkbenchSession:
    """一次可观测、可干预、可分叉的研究会话。"""

    id: str
    topic: str
    status: str = "pending"  # pending / running / paused / completed / failed
    cognitive: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    parent_id: Optional[str] = None
    fork_event_id: Optional[str] = None
    snapshots: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    intervention_queue: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 运行时填充
    state: Optional[ResearchState] = None
    emitter: Optional[TraceEmitter] = None
    _pause_event: Optional[threading.Event] = None
    _stop_event: Optional[threading.Event] = None

    def __post_init__(self):
        if self._pause_event is None:
            self._pause_event = threading.Event()
            self._pause_event.set()
        if self._stop_event is None:
            self._stop_event = threading.Event()

    @classmethod
    def create(
        cls,
        topic: str,
        cognitive: bool = True,
        parent_id: Optional[str] = None,
        fork_event_id: Optional[str] = None,
        data_dir: str = "data/workbench",
    ) -> "WorkbenchSession":
        session_id = f"wb_{uuid.uuid4().hex[:12]}"
        session = cls(
            id=session_id,
            topic=topic,
            cognitive=cognitive,
            parent_id=parent_id,
            fork_event_id=fork_event_id,
        )
        session.emitter = TraceEmitter(session_id, data_dir=data_dir)
        return session

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "topic": self.topic,
            "status": self.status,
            "cognitive": self.cognitive,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "parent_id": self.parent_id,
            "fork_event_id": self.fork_event_id,
            "snapshots": self.snapshots,
            "intervention_queue": self.intervention_queue,
            "metadata": self.metadata,
        }

    def save(self, data_dir: str = "data/workbench"):
        path = Path(data_dir) / f"{self.id}.json"
        try:
            path.write_text(
                json.dumps(self.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("保存会话失败: %s", exc)

    @classmethod
    def load(cls, session_id: str, data_dir: str = "data/workbench") -> Optional["WorkbenchSession"]:
        path = Path(data_dir) / f"{session_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            session = cls(
                id=data["id"],
                topic=data["topic"],
                status=data.get("status", "pending"),
                cognitive=data.get("cognitive", True),
                created_at=data.get("created_at", datetime.now().isoformat()),
                updated_at=data.get("updated_at", datetime.now().isoformat()),
                parent_id=data.get("parent_id"),
                fork_event_id=data.get("fork_event_id"),
                snapshots=data.get("snapshots", {}),
                intervention_queue=data.get("intervention_queue", []),
                metadata=data.get("metadata", {}),
            )
            session.emitter = TraceEmitter(session_id, data_dir=data_dir)
            session.emitter.load_events()
            return session
        except Exception as exc:
            logger.warning("加载会话失败: %s", exc)
            return None

    def add_snapshot(self, event_id: str, state: ResearchState, label: str = ""):
        self.snapshots[event_id] = {
            "event_id": event_id,
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "state": state.to_dict(),
        }
        self.save()

    def get_snapshot(self, event_id: str) -> Optional[ResearchState]:
        snap = self.snapshots.get(event_id)
        if not snap:
            return None
        try:
            return ResearchState.from_dict(snap["state"])
        except Exception as exc:
            logger.warning("恢复快照失败: %s", exc)
            return None

    def request_intervention(self, action: str, payload: Dict[str, Any]):
        self.intervention_queue.append(
            {"action": action, "payload": payload, "requested_at": datetime.now().isoformat()}
        )
        self.save()

    def take_interventions(self) -> List[Dict[str, Any]]:
        items = list(self.intervention_queue)
        self.intervention_queue.clear()
        self.save()
        return items

    def checkpoint(self, event: TraceEvent, state: ResearchState):
        """在检查点处暂停，等待继续信号。"""
        self.add_snapshot(event.id, state, label="checkpoint")
        self.status = "paused"
        self.save()
        if self._pause_event:
            self._pause_event.clear()
            self._pause_event.wait()
        self.status = "running"
        self.save()

    def resume(self):
        if self._pause_event:
            self._pause_event.set()
        self.status = "running"
        self.save()

    def pause(self):
        if self._pause_event:
            self._pause_event.clear()
        self.status = "paused"
        self.save()

    def stop(self):
        if self._stop_event:
            self._stop_event.set()
        self.status = "failed"
        self.save()

    def should_stop(self) -> bool:
        return self._stop_event.is_set() if self._stop_event else False

    def update_metadata(self, key: str, value: Any):
        self.metadata[key] = value
        self.updated_at = datetime.now().isoformat()
        self.save()

    def to_graph(self) -> Dict[str, Any]:
        """将会话事件转换为前端图谱数据。"""
        events = self.emitter.load_events() if self.emitter else []
        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_map: Dict[str, int] = {}

        def ensure_node(node_id: str, label: str, kind: str, payload: Dict[str, Any]):
            if node_id in node_map:
                return node_map[node_id]
            idx = len(nodes)
            node_map[node_id] = idx
            nodes.append(
                {
                    "id": node_id,
                    "label": label,
                    "kind": kind,
                    "payload": payload,
                }
            )
            return idx

        for event in events:
            payload = event.payload or {}
            kind = event.type.value
            label = payload.get("label") or payload.get("description") or payload.get("query") or event.type.value
            ensure_node(event.node_id, label, kind, payload)

            if event.parent_id and event.parent_id in node_map:
                edges.append(
                    {
                        "source": event.parent_id,
                        "target": event.node_id,
                        "type": event.type.value,
                    }
                )

        return {"nodes": nodes, "edges": edges, "session_id": self.id, "status": self.status}
