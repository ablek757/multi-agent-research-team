"""研究成果知识库 FastAPI 服务。"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from kb import KnowledgeStore, parse_markdown_report

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="研究成果知识库",
    description="Multi-Agent 深度研究报告的可视化与检索 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = KnowledgeStore(data_dir="data")


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
    return store.get_stats()


@app.get("/api/reports")
def list_reports(
    q: Optional[str] = Query(None, description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    return store.list_reports(query=q, limit=limit, offset=offset)


@app.get("/api/reports/{report_id}")
def get_report(report_id: str):
    report = store.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    return report.to_storage()


@app.delete("/api/reports/{report_id}")
def delete_report(report_id: str):
    ok = store.delete_report(report_id)
    if not ok:
        raise HTTPException(status_code=404, detail="报告不存在")
    return {"deleted": True}


@app.post("/api/reports/ingest")
def ingest_reports(request: IngestRequest):
    ids = store.ingest_directory(request.directory, request.pattern)
    return {"ingested": len(ids), "report_ids": ids}


@app.post("/api/reports")
def create_report(request: ReportCreate):
    if not Path(request.markdown_path).exists():
        raise HTTPException(status_code=400, detail="Markdown 文件不存在")
    report = parse_markdown_report(
        markdown_path=request.markdown_path,
        state_path=request.state_path,
    )
    store.add_report(report)
    return report.to_storage()


@app.get("/api/search")
def search_reports(q: str = Query(..., min_length=1), top_k: int = Query(20, ge=1, le=100)):
    return store.search_reports(query=q, top_k=top_k)


@app.get("/api/graph")
def get_graph(
    min_edge_weight: int = Query(1, ge=1),
    top_n_nodes: int = Query(100, ge=10, le=300),
):
    return store.get_graph(min_edge_weight=min_edge_weight, top_n_nodes=top_n_nodes)


@app.get("/api/timeline")
def get_timeline() -> List[Dict[str, Any]]:
    return store.get_timeline()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
