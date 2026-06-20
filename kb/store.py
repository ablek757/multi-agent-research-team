"""知识库存储。"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from kb.analyzer import build_topic_graph, merge_entities, merge_topics
from kb.models import Entity, Event, KnowledgeBase, Report
from kb.search import KnowledgeSearch

logger = logging.getLogger(__name__)


class KnowledgeStore:
    """基于 JSONL 文件的研究知识库。"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.kb_file = self.data_dir / "kb.jsonl"
        self.index_file = self.data_dir / "index.json"

        self.kb = KnowledgeBase()
        self.search = KnowledgeSearch()
        self._load()

    def _load(self):
        """从 JSONL 加载知识库。"""
        if not self.kb_file.exists():
            return

        with self.kb_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    report = Report.from_storage(data)
                    self._add_to_memory(report, persist=False)
                except Exception as exc:
                    logger.warning("加载知识库记录失败: %s", exc)

        logger.info("已加载 %d 份报告到知识库", len(self.kb.reports))

    def _persist_report(self, report: Report):
        """追加保存单条报告。"""
        with self.kb_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(report.to_storage(), ensure_ascii=False) + "\n")

    def _rewrite_kb(self):
        """重写整个知识库文件。"""
        with self.kb_file.open("w", encoding="utf-8") as f:
            for report in self.kb.reports.values():
                f.write(json.dumps(report.to_storage(), ensure_ascii=False) + "\n")

    def _add_to_memory(self, report: Report, persist: bool = True):
        """将报告加入内存索引。"""
        self.kb.reports[report.id] = report
        merge_entities(self.kb.entities, report)
        merge_topics(self.kb.topics, report)
        self.search.index_report(report)

        if persist:
            self._persist_report(report)
            self.kb.updated_at = datetime.now().isoformat()

    def add_report(self, report: Report) -> Report:
        """添加或更新报告。"""
        if report.id in self.kb.reports:
            self.delete_report(report.id)
        self._add_to_memory(report, persist=True)
        return report

    def delete_report(self, report_id: str) -> bool:
        """删除报告并重建索引。"""
        if report_id not in self.kb.reports:
            return False

        del self.kb.reports[report_id]
        self.kb.entities.clear()
        self.kb.topics.clear()
        self.search.clear()

        for report in self.kb.reports.values():
            merge_entities(self.kb.entities, report)
            merge_topics(self.kb.topics, report)
            self.search.index_report(report)

        self._rewrite_kb()
        return True

    def get_report(self, report_id: str) -> Optional[Report]:
        return self.kb.reports.get(report_id)

    def list_reports(
        self,
        query: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Dict[str, Any]:
        if query:
            results = self.search.search(query, top_k=limit + offset)
            report_ids = [r["report_id"] for r in results[offset:]]
            total = len(results)
        else:
            sorted_reports = sorted(
                self.kb.reports.values(),
                key=lambda r: r.created_at,
                reverse=True,
            )
            total = len(sorted_reports)
            report_ids = [r.id for r in sorted_reports[offset : offset + limit]]

        reports = [self.kb.reports[rid] for rid in report_ids if rid in self.kb.reports]
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "reports": [r.to_storage() for r in reports],
        }

    def search_reports(self, query: str, top_k: int = 20) -> List[Dict[str, Any]]:
        results = self.search.search(query, top_k=top_k)
        enriched = []
        for item in results:
            report = self.kb.reports.get(item["report_id"])
            if report:
                enriched.append(
                    {
                        "report": report.to_storage(),
                        "score": item["score"],
                    }
                )
        return enriched

    def get_graph(
        self,
        min_edge_weight: int = 1,
        top_n_nodes: int = 100,
    ) -> Dict[str, Any]:
        reports = list(self.kb.reports.values())
        return build_topic_graph(
            reports,
            min_edge_weight=min_edge_weight,
            top_n_nodes=top_n_nodes,
        )

    def get_timeline(self) -> List[Dict[str, Any]]:
        events: List[Event] = []
        for report in self.kb.reports.values():
            events.extend(report.events)
        events.sort(key=lambda e: (e.date_iso or "9999", e.date_text))
        return [e.model_dump() for e in events]

    def get_stats(self) -> Dict[str, Any]:
        return {
            "report_count": len(self.kb.reports),
            "entity_count": len(self.kb.entities),
            "topic_count": len(self.kb.topics),
            "source_count": sum(len(r.sources) for r in self.kb.reports.values()),
            "finding_count": sum(len(r.findings) for r in self.kb.reports.values()),
            "event_count": sum(len(r.events) for r in self.kb.reports.values()),
            "updated_at": self.kb.updated_at,
        }

    def ingest_directory(self, directory: str, pattern: str = "*.md") -> List[str]:
        """批量导入目录中的 Markdown 报告。"""
        dir_path = Path(directory)
        ingested: List[str] = []
        for md_file in sorted(dir_path.glob(pattern)):
            state_file = md_file.with_suffix(".json")
            state_path = str(state_file) if state_file.exists() else None
            try:
                from kb.parser import parse_markdown_report

                report = parse_markdown_report(
                    markdown_path=str(md_file),
                    state_path=state_path,
                )
                self.add_report(report)
                ingested.append(report.id)
            except Exception as exc:
                logger.warning("导入报告失败 %s: %s", md_file, exc)
        return ingested

    def clear_all(self):
        """清空知识库。"""
        self.kb.reports.clear()
        self.kb.entities.clear()
        self.kb.topics.clear()
        self.search.clear()
        if self.kb_file.exists():
            self.kb_file.unlink()
