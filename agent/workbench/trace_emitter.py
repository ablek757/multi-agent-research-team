"""事件发射器：负责创建、持久化与广播研究过程事件。"""

import json
import logging
import queue
import threading
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from agent.workbench.trace_models import TraceEvent, TraceEventType

logger = logging.getLogger(__name__)


class TraceEmitter:
    """将研究过程转换为结构化事件并持久化。"""

    def __init__(
        self,
        session_id: str,
        data_dir: str = "data/workbench",
        broadcast: Optional[Callable[[TraceEvent], None]] = None,
    ):
        self.session_id = session_id
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.events_file = self.data_dir / f"{session_id}.jsonl"
        self.broadcast = broadcast
        self._events: List[TraceEvent] = []
        self._lock = threading.Lock()
        self._subscribers: List[queue.Queue] = []

    def emit(
        self,
        type: TraceEventType,
        payload: Optional[Dict[str, Any]] = None,
        parent_id: Optional[str] = None,
        node_id: Optional[str] = None,
        agent: Optional[str] = None,
    ) -> TraceEvent:
        event = TraceEvent.create(
            session_id=self.session_id,
            type=type,
            payload=payload,
            parent_id=parent_id,
            node_id=node_id,
            agent=agent,
        )
        with self._lock:
            self._events.append(event)
            self._append_to_file(event)
            self._notify_subscribers(event)
        if self.broadcast:
            try:
                self.broadcast(event)
            except Exception as exc:
                logger.warning("事件广播失败: %s", exc)
        return event

    def _append_to_file(self, event: TraceEvent):
        try:
            with self.events_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("事件持久化失败: %s", exc)

    def _notify_subscribers(self, event: TraceEvent):
        for q in list(self._subscribers):
            try:
                q.put_nowait(event)
            except queue.Full:
                pass

    def subscribe(self, maxsize: int = 1000) -> queue.Queue:
        q: queue.Queue = queue.Queue(maxsize=maxsize)
        with self._lock:
            for event in self._events:
                q.put(event)
            self._subscribers.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._subscribers:
                self._subscribers.remove(q)

    def load_events(self) -> List[TraceEvent]:
        events: List[TraceEvent] = []
        if not self.events_file.exists():
            return events
        try:
            with self.events_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        events.append(TraceEvent.from_dict(json.loads(line)))
                    except Exception as exc:
                        logger.warning("加载事件失败: %s", exc)
        except Exception as exc:
            logger.warning("读取事件文件失败: %s", exc)
        with self._lock:
            self._events = events
        return events

    def latest_event(self) -> Optional[TraceEvent]:
        with self._lock:
            return self._events[-1] if self._events else None
