"""认知探索工作台引擎：包装研究执行，支持观测、干预与分叉。"""

import logging
import threading
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from agent.cognition import CognitiveController
from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import TeamOrchestrator
from agent.research_state import ResearchState
from agent.workbench.session import WorkbenchSession
from agent.workbench.trace_models import TraceEventType
from agent.workbench.trace_emitter import TraceEmitter

logger = logging.getLogger(__name__)

TraceCallback = Callable[[TraceEventType, Dict[str, Any], Optional[str], Optional[str], Optional[str]], None]


class WorkbenchEngine:
    """驱动一次可观测的研究会话。"""

    def __init__(
        self,
        config: Config,
        llm: LLMClient,
        kb_store=None,
        data_dir: str = "data/workbench",
    ):
        self.config = config
        self.llm = llm
        self.kb_store = kb_store
        self.data_dir = data_dir
        self._sessions: Dict[str, WorkbenchSession] = {}
        self._lock = threading.Lock()
        self._load_sessions()

    def _load_sessions(self):
        path = Path(self.data_dir)
        if not path.exists():
            return
        for file in path.glob("wb_*.json"):
            session_id = file.stem
            session = WorkbenchSession.load(session_id, data_dir=self.data_dir)
            if session:
                self._sessions[session_id] = session

    def create_session(
        self,
        topic: str,
        cognitive: bool = True,
        parent_id: Optional[str] = None,
        fork_event_id: Optional[str] = None,
        initial_state: Optional[ResearchState] = None,
    ) -> WorkbenchSession:
        session = WorkbenchSession.create(
            topic=topic,
            cognitive=cognitive,
            parent_id=parent_id,
            fork_event_id=fork_event_id,
            data_dir=self.data_dir,
        )
        session.state = initial_state or ResearchState()
        session.save(self.data_dir)
        with self._lock:
            self._sessions[session.id] = session
        return session

    def get_session(self, session_id: str) -> Optional[WorkbenchSession]:
        with self._lock:
            session = self._sessions.get(session_id)
        if not session:
            session = WorkbenchSession.load(session_id, data_dir=self.data_dir)
            if session:
                with self._lock:
                    self._sessions[session_id] = session
        return session

    def list_sessions(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "sessions": [
                    {
                        "id": s.id,
                        "topic": s.topic,
                        "status": s.status,
                        "created_at": s.created_at,
                        "updated_at": s.updated_at,
                        "parent_id": s.parent_id,
                    }
                    for s in self._sessions.values()
                ]
            }

    def _make_trace_callback(self, session: WorkbenchSession) -> TraceCallback:
        def callback(
            event_type: TraceEventType,
            payload: Dict[str, Any],
            parent_id: Optional[str] = None,
            node_id: Optional[str] = None,
            agent: Optional[str] = None,
        ):
            if session.should_stop():
                raise RuntimeError("会话已被用户终止")

            if session.emitter:
                event = session.emitter.emit(
                    type=event_type,
                    payload=payload,
                    parent_id=parent_id,
                    node_id=node_id,
                    agent=agent,
                )

                # 处理用户干预
                self._apply_interventions(session)

                # 在检查点处暂停并保存快照
                if event_type == TraceEventType.CHECKPOINT and session.state:
                    session.checkpoint(event, session.state)

        return callback

    def _apply_interventions(self, session: WorkbenchSession):
        """将用户干预请求应用到当前会话状态。"""
        if not session.state:
            return
        for item in session.take_interventions():
            action = item.get("action")
            payload = item.get("payload", {})
            if action == "inject_query":
                query = payload.get("query", "").strip()
                if query and query not in session.state.open_questions:
                    session.state.open_questions.append(query)
            elif action == "inject_gap":
                gap = payload.get("gap", "").strip()
                if gap and gap not in session.state.gaps:
                    session.state.gaps.append(gap)
            elif action == "set_theme":
                theme = payload.get("theme", "").strip()
                if theme and theme not in session.state.themes:
                    session.state.themes.append(theme)
            logger.info("已应用干预: %s", action)

    def _build_progress_callback(self, session: WorkbenchSession, trace_cb: TraceCallback):
        original_progress = lambda msg: None

        def progress(message: str):
            original_progress(message)
            # 将文本进度也作为 agent_action 事件记录，便于追溯
            if session.emitter:
                session.emitter.emit(
                    type=TraceEventType.AGENT_ACTION,
                    payload={"message": message},
                    agent="system",
                )
        return progress

    def run_session_sync(self, session: WorkbenchSession):
        """同步运行会话（适合后台任务调用）。"""
        session.status = "running"
        session.save(self.data_dir)
        trace_cb = self._make_trace_callback(session)
        progress_cb = self._build_progress_callback(session, trace_cb)

        if session.emitter:
            session.emitter.emit(
                type=TraceEventType.SESSION_STARTED,
                payload={"topic": session.topic, "cognitive": session.cognitive},
            )

        try:
            if session.cognitive:
                controller = CognitiveController(
                    config=self.config,
                    llm=self.llm,
                    progress_callback=progress_cb,
                    kb_store=self.kb_store,
                    trace_callback=trace_cb,
                )
                final_state = controller.run(session.topic)
            else:
                orchestrator = TeamOrchestrator(
                    self.config,
                    progress_callback=progress_cb,
                    trace_callback=trace_cb,
                )
                final_state = orchestrator.run(session.topic)

            session.state = final_state
            session.update_metadata(
                "summary",
                {
                    "sources": len(final_state.sources),
                    "findings": len(final_state.findings),
                    "entities": len(final_state.entities),
                    "queries": len(final_state.open_questions),
                    "score": final_state.metrics.get("overall_score") if final_state.metrics else None,
                },
            )
            session.status = "completed"
            if session.emitter:
                session.emitter.emit(
                    type=TraceEventType.SESSION_COMPLETED,
                    payload={"summary": session.metadata.get("summary", {})},
                )
        except Exception as exc:
            logger.error("工作台会话执行失败: %s", exc)
            session.status = "failed"
            if session.emitter:
                session.emitter.emit(
                    type=TraceEventType.SESSION_FAILED,
                    payload={"error": str(exc)},
                )
        finally:
            session.save(self.data_dir)

    def start_session(self, session: WorkbenchSession):
        """在后台线程启动会话。"""
        thread = threading.Thread(
            target=self.run_session_sync,
            args=(session,),
            daemon=True,
        )
        thread.start()

    def intervene(self, session_id: str, action: str, payload: Dict[str, Any]) -> bool:
        session = self.get_session(session_id)
        if not session:
            return False

        if action == "resume":
            session.resume()
        elif action == "pause":
            session.pause()
        elif action == "stop":
            session.stop()
        else:
            session.request_intervention(action, payload)

        if session.emitter:
            session.emitter.emit(
                type=TraceEventType.INTERVENTION,
                payload={"action": action, "payload": payload},
            )
        return True

    def fork(self, session_id: str, event_id: str, topic: Optional[str] = None) -> Optional[WorkbenchSession]:
        parent = self.get_session(session_id)
        if not parent or not parent.emitter:
            return None

        snapshot = parent.get_snapshot(event_id)
        if not snapshot:
            # 尝试从事件附带的最新状态分叉
            snapshot = parent.state or ResearchState()

        new_session = self.create_session(
            topic=topic or parent.topic,
            cognitive=parent.cognitive,
            parent_id=session_id,
            fork_event_id=event_id,
            initial_state=snapshot,
        )

        # 继承父会话的事件历史作为只读上下文
        if parent.emitter:
            parent_events = parent.emitter.load_events()
            for event in parent_events:
                if event.id == event_id:
                    break
                if new_session.emitter:
                    new_session.emitter.emit(
                        type=event.type,
                        payload={**event.payload, "inherited": True},
                        parent_id=event.parent_id,
                        node_id=event.node_id,
                        agent=event.agent,
                    )

        if new_session.emitter:
            new_session.emitter.emit(
                type=TraceEventType.FORK,
                payload={"parent_id": session_id, "fork_event_id": event_id},
            )
        new_session.save(self.data_dir)
        return new_session

    def subscribe_events(self, session_id: str):
        session = self.get_session(session_id)
        if not session or not session.emitter:
            return None
        return session.emitter.subscribe()
