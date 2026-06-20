"""知识库数据模型。"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Source(BaseModel):
    index: int
    title: str
    url: str
    snippet: str = ""


class Finding(BaseModel):
    text: str
    source_index: Optional[int] = None
    source_url: Optional[str] = None
    confidence: Optional[float] = None  # 可信验证分数（0-100）


class Topic(BaseModel):
    id: str
    name: str
    report_ids: List[str] = Field(default_factory=list)
    count: int = 1


class Entity(BaseModel):
    id: str
    name: str
    report_ids: List[str] = Field(default_factory=list)
    count: int = 1


class Relation(BaseModel):
    source: str
    target: str
    weight: int = 1
    report_ids: List[str] = Field(default_factory=list)


class Event(BaseModel):
    id: str
    date_text: str
    date_iso: Optional[str] = None
    description: str
    report_id: str
    report_title: str = ""


class Report(BaseModel):
    id: str
    title: str
    topic: str
    created_at: str
    model: str = ""
    content: str = ""
    sources: List[Source] = Field(default_factory=list)
    findings: List[Finding] = Field(default_factory=list)
    entities: List[Entity] = Field(default_factory=list)
    topics: List[Topic] = Field(default_factory=list)
    events: List[Event] = Field(default_factory=list)
    markdown_path: Optional[str] = None
    state_path: Optional[str] = None

    def to_storage(self) -> Dict[str, Any]:
        return self.model_dump()

    @classmethod
    def from_storage(cls, data: Dict[str, Any]) -> "Report":
        return cls(**data)


class KnowledgeBase(BaseModel):
    reports: Dict[str, Report] = Field(default_factory=dict)
    entities: Dict[str, Entity] = Field(default_factory=dict)
    topics: Dict[str, Topic] = Field(default_factory=dict)
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())
