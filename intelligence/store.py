"""情报本地 JSONL 存储。"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from intelligence.models import Alert, Briefing

logger = logging.getLogger(__name__)


class IntelligenceStore:
    """基于 JSONL 的情报存储。"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.alerts_file = self.data_dir / "intelligence_alerts.jsonl"
        self.briefings_file = self.data_dir / "intelligence_briefings.jsonl"

        self.alerts: Dict[str, Alert] = {}
        self.briefings: Dict[str, Briefing] = {}
        self._load()

    def _load(self):
        self.alerts = self._load_alerts()
        self.briefings = self._load_briefings()
        logger.info(
            "已加载 %d 条告警与 %d 份简报",
            len(self.alerts),
            len(self.briefings),
        )

    def _load_alerts(self) -> Dict[str, Alert]:
        alerts: Dict[str, Alert] = {}
        if not self.alerts_file.exists():
            return alerts
        with self.alerts_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    article_data = data.pop("article", {})
                    scores_data = data.pop("scores", {})
                    from intelligence.models import Article, RelevanceScores

                    alert = Alert(
                        **data,
                        article=Article(**article_data),
                        scores=RelevanceScores(**scores_data),
                    )
                    alerts[alert.id] = alert
                except Exception as exc:
                    logger.warning("加载告警记录失败: %s", exc)
        return alerts

    def _load_briefings(self) -> Dict[str, Briefing]:
        briefings: Dict[str, Briefing] = {}
        if not self.briefings_file.exists():
            return briefings
        with self.briefings_file.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    alerts_data = data.pop("alerts", [])
                    from intelligence.models import Alert, Article, RelevanceScores

                    alerts = [
                        Alert(
                            id=a["id"],
                            topic=a["topic"],
                            article=Article(**a["article"]),
                            scores=RelevanceScores(**a["scores"]),
                            created_at=a.get("created_at"),
                            notified=a.get("notified", False),
                        )
                        for a in alerts_data
                    ]
                    briefing = Briefing(**data, alerts=alerts)
                    briefings[briefing.id] = briefing
                except Exception as exc:
                    logger.warning("加载简报记录失败: %s", exc)
        return briefings

    def add_alert(self, alert: Alert) -> Alert:
        self.alerts[alert.id] = alert
        self._persist_alert(alert)
        return alert

    def _persist_alert(self, alert: Alert):
        with self.alerts_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")

    def add_briefing(self, briefing: Briefing) -> Briefing:
        self.briefings[briefing.id] = briefing
        self._persist_briefing(briefing)
        return briefing

    def _persist_briefing(self, briefing: Briefing):
        with self.briefings_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(briefing.to_dict(), ensure_ascii=False) + "\n")

    def get_alert(self, alert_id: str) -> Optional[Alert]:
        return self.alerts.get(alert_id)

    def get_briefing(self, briefing_id: str) -> Optional[Briefing]:
        return self.briefings.get(briefing_id)

    def list_alerts(
        self,
        topic: Optional[str] = None,
        notified: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        alerts = list(self.alerts.values())
        if topic:
            alerts = [a for a in alerts if a.topic == topic]
        if notified is not None:
            alerts = [a for a in alerts if a.notified == notified]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        total = len(alerts)
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "alerts": [a.to_dict() for a in alerts[offset : offset + limit]],
        }

    def list_briefings(
        self,
        topic: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        briefings = list(self.briefings.values())
        if topic:
            briefings = [b for b in briefings if b.topic == topic]
        briefings.sort(key=lambda b: b.created_at, reverse=True)
        total = len(briefings)
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "briefings": [b.to_dict() for b in briefings[offset : offset + limit]],
        }

    def alert_exists(self, article_id: str, topic: str) -> bool:
        return any(
            a.article.id == article_id and a.topic == topic for a in self.alerts.values()
        )

    def mark_alerts_notified(self, alert_ids: List[str]):
        for alert_id in alert_ids:
            alert = self.alerts.get(alert_id)
            if alert:
                alert.notified = True
        self._rewrite_alerts()

    def _rewrite_alerts(self):
        with self.alerts_file.open("w", encoding="utf-8") as f:
            for alert in self.alerts.values():
                f.write(json.dumps(alert.to_dict(), ensure_ascii=False) + "\n")

    def clear_all(self):
        self.alerts.clear()
        self.briefings.clear()
        if self.alerts_file.exists():
            self.alerts_file.unlink()
        if self.briefings_file.exists():
            self.briefings_file.unlink()
