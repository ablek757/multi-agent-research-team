"""研究成果知识库 FastAPI 服务。"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent.config import Config
from intelligence.scheduler import IntelligenceScheduler
from intelligence.service import IntelligenceService
from intelligence.store import IntelligenceStore
from kb import KnowledgeStore, parse_markdown_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="研究成果知识库",
    description="Multi-Agent 深度研究报告与实时情报系统的可视化与检索 API",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

config = Config.load("config.yaml")
kb_store = KnowledgeStore(data_dir=config.kb.data_dir)
intelligence_store = IntelligenceStore(data_dir=config.kb.data_dir)
intelligence_service = IntelligenceService(
    config,
    kb_store=kb_store,
    intelligence_store=intelligence_store,
)
intelligence_scheduler: Optional[IntelligenceScheduler] = None
if config.intelligence.enabled:
    intelligence_scheduler = IntelligenceScheduler(config, intelligence_service)
    intelligence_scheduler.start()


class IngestRequest(BaseModel):
    directory: str = "output"
    pattern: str = "*.md"


class ReportCreate(BaseModel):
    markdown_path: str
    state_path: Optional[str] = None


@app.get("/")
def root():
    return {
        "message": "研究成果知识库 API",
        "docs": "/docs",
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


@app.get("/api/graph")
def get_graph(
    min_edge_weight: int = Query(1, ge=1),
    top_n_nodes: int = Query(100, ge=10, le=300),
):
    return kb_store.get_graph(min_edge_weight=min_edge_weight, top_n_nodes=top_n_nodes)


@app.get("/api/timeline")
def get_timeline() -> List[Dict[str, Any]]:
    return kb_store.get_timeline()


class ScanRequest(BaseModel):
    topics: Optional[List[str]] = None


@app.get("/api/intelligence/topics")
def list_intelligence_topics() -> Dict[str, Any]:
    topics = intelligence_service.get_monitor_topics()
    return {"topics": topics}


@app.get("/api/intelligence/alerts")
def list_alerts(
    topic: Optional[str] = Query(None),
    notified: Optional[bool] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
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
    return intelligence_service.list_briefings(topic=topic, limit=limit, offset=offset)


@app.post("/api/intelligence/run")
def run_intelligence_scan(request: ScanRequest):
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
