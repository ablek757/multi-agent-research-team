import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml


@dataclass
class LLMConfig:
    api_key: str = ""
    base_url: Optional[str] = None
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 4096


@dataclass
class SearchConfig:
    backend: str = "duckduckgo"
    results_per_query: int = 5
    top_k_to_fetch: int = 3
    max_workers: int = 5
    region: str = "wt-wt"
    safe_search: str = "moderate"


@dataclass
class ResearchConfig:
    depth: int = 2
    queries_per_round: int = 3
    max_content_length: int = 12000
    language: str = "zh"


@dataclass
class ReportConfig:
    title: str = "深度研究报告"
    output_dir: str = "output"
    include_citations: bool = True


@dataclass
class Config:
    llm: LLMConfig = field(default_factory=LLMConfig)
    search: SearchConfig = field(default_factory=SearchConfig)
    research: ResearchConfig = field(default_factory=ResearchConfig)
    report: ReportConfig = field(default_factory=ReportConfig)

    @classmethod
    def load(cls, path: str = "config.yaml") -> "Config":
        config_path = Path(path)
        data: dict = {}
        if config_path.exists():
            with config_path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        llm_data = data.get("llm", {})
        llm_data["api_key"] = os.getenv("OPENAI_API_KEY", llm_data.get("api_key", ""))
        llm_data["base_url"] = os.getenv("OPENAI_BASE_URL", llm_data.get("base_url"))
        llm_data["model"] = os.getenv("OPENAI_MODEL", llm_data.get("model", "gpt-4o-mini"))

        return cls(
            llm=LLMConfig(**llm_data),
            search=SearchConfig(**data.get("search", {})),
            research=ResearchConfig(**data.get("research", {})),
            report=ReportConfig(**data.get("report", {})),
        )

    def validate(self) -> None:
        if not self.llm.api_key:
            raise ValueError(
                "LLM API key is required. Set OPENAI_API_KEY environment variable or fill config.yaml."
            )
        if self.research.depth < 1:
            raise ValueError("research.depth must be at least 1")
        if self.search.top_k_to_fetch > self.search.results_per_query:
            raise ValueError("search.top_k_to_fetch cannot exceed search.results_per_query")
