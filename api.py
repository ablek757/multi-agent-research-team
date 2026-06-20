"""认知增强型研究执行与创作系统 FastAPI 服务。"""

import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agent.cognition import CognitiveController
from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import ResearchOrchestrator
from agent.output import get_formatter, list_formats
from agent.report import generate_report, save_report, save_state
from agent.style import StyleLearner
from kb import KnowledgeStore, parse_markdown_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="认知增强型研究执行与创作系统",
    description="Multi-Agent 深度研究、知识库、实时情报与多模态创作 API",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config.load("config.yaml")
kb_store = KnowledgeStore(
    data_dir=config.kb.data_dir,
    memory_config=config.memory,
    llm_config=config.llm,
)

intelligence_store = None
intelligence_service = None
intelligence_scheduler = None
try:
    from intelligence.scheduler import IntelligenceScheduler
    from intelligence.service import IntelligenceService
    from intelligence.store import IntelligenceStore

    intelligence_store = IntelligenceStore(data_dir=config.kb.data_dir)
    intelligence_service = IntelligenceService(
        config,
        kb_store=kb_store,
        intelligence_store=intelligence_store,
    )
    if config.intelligence.enabled:
        intelligence_scheduler = IntelligenceScheduler(config, intelligence_service)
        intelligence_scheduler.start()
except Exception as exc:
    logger.warning("情报模块初始化失败: %s", exc)


# 简单内存任务存储（原型级别）
_jobs: Dict[str, Dict[str, Any]] = {}


class IngestRequest(BaseModel):
    directory: str = "output"
    pattern: str = "*.md"


class ReportCreate(BaseModel):
    markdown_path: str
    state_path: Optional[str] = None


class ResearchRequest(BaseModel):
    topic: str
    cognitive: bool = Field(default=False, description="是否启用认知增强模式")
    formats: Optional[List[str]] = Field(default=None, description="输出格式列表")
    depth: Optional[int] = None


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = 10


class StyleLearnRequest(BaseModel):
    original: str = ""
    revised: str = ""
    feedback: str = ""


class OutputConvertRequest(BaseModel):
    topic: str
    markdown_path: Optional[str] = None
    state_path: Optional[str] = None


@app.get("/")
def root():
    return {
        "message": "认知增强型研究执行与创作系统 API",
        "docs": "/docs",
        "version": "0.3.0",
    }


@app.get("/api/stats")
def get_stats() -> Dict[str, Any]:
    return kb_store.get_stats()


@app.get("/api/reports")
def list_reports(
    q: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return kb_store.list_reports(query=q, limit=limit, offset=offset)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    report = kb_store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report.to_storage()


@app.get("/api/reports/{report_id}/related")
def get_related_reports(report_id: str, top_k: int = Query(10, ge=1, le=50)):
    reports = kb_store.find_related_reports(report_id, top_k=top_k)
    return {"reports": reports}


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str):
    ok = kb_store.delete_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"deleted": True}


@app.post("/api/reports/ingest")
def ingest_reports(request: IngestRequest):
    ids = kb_store.ingest_directory(request.directory, request.pattern)
    return {"ingested": len(ids), "report_ids": ids}


@app.post("/api/reports")
def create_report(request: ReportCreate):
    if not Path(request.markdown_path).exists():
        raise HTTPException(status_code=400, detail="Markdown 文件不存在")
    report = parse_markdown_report(
        markdown_path=request.markdown_path,
        state_path=request.state_path,
    )
    kb_store.add_report(report)
    return report.to_storage()


@app.get("/api/search")
def search_reports(q: str = Query(..., min_length=1), top_k: int = Query(20, ge=1, le=100)):
    return kb_store.search_reports(query=q, top_k=top_k)


@app.post("/api/memory/search")
def semantic_search(request: MemorySearchRequest):
    results = kb_store.semantic_search(request.query, top_k=request.top_k)
    return {"query": request.query, "results": results}


@app.get("/api/graph")
def get_graph(
    min_edge_weight: int = Query(1, ge=1),
    top_n_nodes: int = Query(100, ge=10, le=300),
):
    return kb_store.get_graph(min_edge_weight=min_edge_weight, top_n_nodes=top_n_nodes)


@app.get("/api/timeline")
def get_timeline() -> List[Dict[str, Any]]:
    return kb_store.get_timeline()


@app.get("/api/formats")
def list_output_formats():
    return {"formats": list_formats()}


def _run_research_job(job_id: str, topic: str, cognitive: bool, formats: List[str], depth: Optional[int]):
    """后台执行研究任务。"""
    _jobs[job_id]["status"] = "running"
    try:
        run_config = Config.load("config.yaml")
        if depth is not None:
            run_config.research.depth = depth
        run_config.cognition.enabled = cognitive
        run_config.output.formats = formats or ["markdown"]
        run_config.validate()

        llm_client = LLMClient(run_config.llm)

        def on_progress(message: str):
            _jobs[job_id].setdefault("logs", []).append(message)

        if cognitive:
            controller = CognitiveController(
                config=run_config,
                llm=llm_client,
                progress_callback=on_progress,
                kb_store=kb_store,
            )
            state = controller.run(topic)
        else:
            orchestrator = ResearchOrchestrator(run_config, progress_callback=on_progress)
            state = orchestrator.run(topic)

        # 生成多格式输出
        output_paths = []
        safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in topic)[:50]
        output_dir = Path(run_config.report.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        state_path = str(output_dir / f"{safe_name}_{job_id[:8]}.json")
        save_state(state, state_path)

        for fmt in run_config.output.formats:
            try:
                formatter = get_formatter(fmt, run_config)
                artifact = formatter.format(topic, state)
                if artifact.file_path:
                    output_paths.append({"format": fmt, "path": artifact.file_path})
                elif fmt == "markdown":
                    report = generate_report(topic, state, run_config, llm_client)
                    md_path = str(output_dir / f"{safe_name}_{job_id[:8]}.md")
                    save_report(report, md_path)
                    output_paths.append({"format": fmt, "path": md_path})
            except Exception as exc:
                logger.warning("生成 %s 格式失败: %s", fmt, exc)
                output_paths.append({"format": fmt, "error": str(exc)})

        _jobs[job_id].update(
            {
                "status": "completed",
                "sources": len(state.sources),
                "findings": len(state.findings),
                "metrics": state.metrics,
                "outputs": output_paths,
                "state_path": state_path,
            }
        )

        # 自动导入知识库
        if run_config.kb.auto_ingest:
            try:
                md_artifact = next((o for o in output_paths if o.get("format") == "markdown"), None)
                if md_artifact and "path" in md_artifact:
                    report = parse_markdown_report(
                        markdown_path=md_artifact["path"],
                        state_path=state_path,
                    )
                    kb_store.add_report(report)
            except Exception as exc:
                logger.warning("自动导入知识库失败: %s", exc)

    except Exception as exc:
        logger.error("研究任务失败: %s", exc)
        _jobs[job_id].update({"status": "failed", "error": str(exc)})


@app.post("/api/research")
def start_research(request: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {
        "job_id": job_id,
        "topic": request.topic,
        "status": "queued",
        "created_at": datetime.now().isoformat(),
    }
    background_tasks.add_task(
        _run_research_job,
        job_id,
        request.topic,
        request.cognitive,
        request.formats or config.output.formats,
        request.depth,
    )
    return {"job_id": job_id, "status": "queued"}


@app.get("/api/research/{job_id}")
def get_research_status(job_id: str):
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="任务不存在")
    return job


@app.get("/api/style/profile")
def get_style_profile():
    try:
        learner = StyleLearner(config.style)
        profile = learner.load_profile()
        return profile.to_storage()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/style/learn")
def learn_style(request: StyleLearnRequest):
    try:
        learner = StyleLearner(config.style, LLMClient(config.llm))
        if request.revised:
            profile = learner.learn_from_edits(request.original, request.revised)
        elif request.feedback:
            profile = learner.learn_from_feedback(request.original, request.feedback)
        else:
            raise HTTPException(status_code=400, detail="请提供 original+revised 或 original+feedback")
        return profile.to_storage()
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/output/{format_name}")
def convert_output(format_name: str, request: OutputConvertRequest):
    if format_name not in list_formats():
        raise HTTPException(status_code=400, detail=f"不支持的格式: {format_name}")
    if request.markdown_path and not Path(request.markdown_path).exists():
        raise HTTPException(status_code=400, detail="Markdown 文件不存在")
    try:
        report = parse_markdown_report(
            markdown_path=request.markdown_path,
            state_path=request.state_path,
        )
        # 构造 ResearchState 以复用 formatter
        from agent.research_state import ResearchState

        state = ResearchState()
        state.report_body = report.content
        state.sources = report.sources
        state.findings = [f.text for f in report.findings]
        state.entities = [e.name for e in report.entities]

        formatter = get_formatter(format_name, config)
        artifact = formatter.format(request.topic, state)
        return {
            "format": format_name,
            "file_path": artifact.file_path,
            "metadata": artifact.metadata,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class ScanRequest(BaseModel):
    topics: Optional[List[str]] = None


@app.get("/api/intelligence/topics")
def list_intelligence_topics() -> Dict[str, Any]:
    if intelligence_service is None:
        raise HTTPException(status_code=503, detail="情报服务未初始化")
    topics = intelligence_service.get_monitor_topics()
    return {"topics": topics}


@app.get("/api/intelligence/alerts")
def list_alerts(
    topic: Optional[str] = Query(None),
    notified: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if intelligence_service is None:
        raise HTTPException(status_code=503, detail="情报服务未初始化")
    return intelligence_service.list_alerts(
        topic=topic,
        notified=notified,
        limit=limit,
        offset=offset,
    )


@app.get("/api/intelligence/briefings")
def list_briefings(
    topic: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    if intelligence_service is None:
        raise HTTPException(status_code=503, detail="情报服务未初始化")
    return intelligence_service.list_briefings(topic=topic, limit=limit, offset=offset)


@app.post("/api/intelligence/run")
def run_intelligence_scan(request: ScanRequest):
    if intelligence_service is None:
        raise HTTPException(status_code=503, detail="情报服务未初始化")
    if not config.intelligence.enabled:
        raise HTTPException(status_code=400, detail="情报系统已禁用")
    try:
        alerts = intelligence_service.run_scan(topics=request.topics)
        return {
            "scanned_topics": list(alerts.keys()),
            "total_alerts": sum(len(v) for v in alerts.values()),
        }
    except Exception as exc:
        logger.error("情报扫描失败: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
