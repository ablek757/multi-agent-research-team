"""7×24 小时情报扫描调度器。"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from agent.config import Config
from intelligence.service import IntelligenceService

logger = logging.getLogger(__name__)


class IntelligenceScheduler:
    """基于 APScheduler 的情报扫描调度器。"""

    def __init__(
        self,
        config: Config,
        service: Optional[IntelligenceService] = None,
    ):
        self.config = config
        self.service = service or IntelligenceService(config)
        self.scheduler = BackgroundScheduler()

    def start(self):
        """启动后台调度。"""
        hours = self.config.intelligence.scan_interval_hours
        self.scheduler.add_job(
            self._scan_job,
            trigger=IntervalTrigger(hours=hours),
            id="intelligence_scan",
            replace_existing=True,
        )
        self.scheduler.start()
        logger.info("情报扫描调度器已启动，间隔 %d 小时", hours)

    def stop(self):
        """停止调度器。"""
        self.scheduler.shutdown()
        logger.info("情报扫描调度器已停止")

    def _scan_job(self):
        logger.info("开始定时情报扫描任务")
        try:
            self.service.run_scan()
        except Exception as exc:
            logger.error("定时情报扫描任务失败: %s", exc)

    def add_manual_job(self, topics: Optional[list] = None):
        """立即手动执行一次扫描。"""
        return self.service.run_scan(topics=topics)
