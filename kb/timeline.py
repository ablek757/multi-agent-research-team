"""时间线与事件抽取。"""

import hashlib
import re
from datetime import datetime
from typing import List, Optional, Tuple

from kb.models import Event


# 中文/英文常见时间模式
DATE_PATTERNS = [
    # 2024年6月15日
    r"(\d{4})年\s*(\d{1,2})月\s*(\d{1,2})日",
    # 2024年6月
    r"(\d{4})年\s*(\d{1,2})月",
    # 2024年
    r"(\d{4})年",
    # 2024-06-15
    r"(\d{4})-(\d{2})-(\d{2})",
    # 2024/06/15
    r"(\d{4})/(\d{2})/(\d{2})",
    # 06/15/2024
    r"(\d{2})/(\d{2})/(\d{4})",
    # June 15, 2024
    r"(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
    # 2024
    r"(?<![\d\-])\b(\d{4})\b(?![\d\-])",
]


def _extract_date_candidates(text: str) -> List[Tuple[str, Optional[Tuple[int, ...]]]]:
    """从文本中提取时间候选。"""
    candidates: List[Tuple[str, Optional[Tuple[int, ...]]]] = []
    seen: set = set()

    for pattern in DATE_PATTERNS:
        for match in re.finditer(pattern, text):
            raw = match.group(0)
            if raw in seen:
                continue
            seen.add(raw)
            groups = match.groups()
            if groups:
                nums = tuple(int(g) for g in groups)
                candidates.append((raw, nums))
            else:
                candidates.append((raw, None))

    return candidates


def _to_iso(nums: Tuple[int, ...]) -> Optional[str]:
    """将数字元组转换为 ISO 日期字符串（可能不完整）。"""
    try:
        if len(nums) == 3:
            year, month, day = nums
            if 1900 <= year <= 2100 and 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
        elif len(nums) == 2:
            year, month = nums
            if 1900 <= year <= 2100 and 1 <= month <= 12:
                return f"{year:04d}-{month:02d}-01"
        elif len(nums) == 1:
            year = nums[0]
            if 1900 <= year <= 2100:
                return f"{year:04d}-01-01"
    except Exception:
        pass
    return None


def _event_id(report_id: str, date_text: str, description: str) -> str:
    text = f"{report_id}::{date_text}::{description}"
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


def _split_sentences(text: str) -> List[str]:
    # 按句号、感叹号、问号分割（中文标点后可无空格）
    sentences = re.split(r"(?<=[。！？.!?])\s*", text)
    return [s.strip() for s in sentences if s.strip()]


def extract_timeline(
    text: str,
    report_id: str = "",
    report_title: str = "",
    max_events: int = 50,
) -> List[Event]:
    """从报告正文中抽取时间事件。"""
    events: List[Event] = []
    seen: set = set()

    sentences = _split_sentences(text)
    for sentence in sentences:
        candidates = _extract_date_candidates(sentence)
        if not candidates:
            continue

        # 抽取句子中每个独立日期作为单独事件
        for raw, nums in candidates:
            iso = _to_iso(nums) if nums else None

            # 截断描述，避免过长
            description = sentence.strip()
            if len(description) > 300:
                description = description[:300] + "..."

            event_key = f"{raw}::{description[:80]}"
            if event_key in seen:
                continue
            seen.add(event_key)

            events.append(
                Event(
                    id=_event_id(report_id, raw, description),
                    date_text=raw,
                    date_iso=iso,
                    description=description,
                    report_id=report_id,
                    report_title=report_title,
                )
            )

            if len(events) >= max_events:
                break
        if len(events) >= max_events:
            break

    # 按 ISO 日期排序
    events.sort(key=lambda e: (e.date_iso or "9999", e.date_text))
    return events
