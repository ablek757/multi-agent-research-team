"""学术源适配器基类。"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import List

from intelligence.models import Article

logger = logging.getLogger(__name__)


class AcademicSource(ABC):
    """学术源抽象接口。"""

    name: str = ""

    @abstractmethod
    def fetch_recent(self, days: int = 1, query: str = "") -> List[Article]:
        """获取最近 days 天内与 query 相关的文章。"""
        raise NotImplementedError

    def _cutoff_date(self, days: int) -> datetime:
        from datetime import timezone

        return datetime.now(timezone.utc) - timedelta(days=days)

    def _is_recent(self, date_str: str, days: int) -> bool:
        """判断日期字符串是否在最近 days 天内。"""
        try:
            dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        except Exception:
            try:
                from dateparser import parse

                dt = parse(date_str)
                if dt is None:
                    return False
            except Exception:
                return False
        return dt >= self._cutoff_date(days)
