"""学术源适配器集合。"""

from typing import Dict, Type

from intelligence.sources.arxiv import ArxivSource
from intelligence.sources.base import AcademicSource
from intelligence.sources.biorxiv import BiorxivSource
from intelligence.sources.openalex import OpenAlexSource
from intelligence.sources.pubmed import PubMedSource
from intelligence.sources.semantic_scholar import SemanticScholarSource

SOURCE_REGISTRY: Dict[str, Type[AcademicSource]] = {
    "arxiv": ArxivSource,
    "pubmed": PubMedSource,
    "biorxiv": BiorxivSource,
    "semantic_scholar": SemanticScholarSource,
    "openalex": OpenAlexSource,
}

__all__ = [
    "AcademicSource",
    "ArxivSource",
    "PubMedSource",
    "BiorxivSource",
    "SemanticScholarSource",
    "OpenAlexSource",
    "SOURCE_REGISTRY",
]
