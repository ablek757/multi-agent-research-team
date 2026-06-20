"""向量 embedding 与语义检索。"""

import json
import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from agent.config import MemoryConfig
from kb.models import Report

logger = logging.getLogger(__name__)


class EmbeddingProvider(ABC):
    """Embedding 提供者抽象。"""

    @abstractmethod
    def embed(self, texts: List[str]) -> np.ndarray:
        """将文本列表编码为向量数组，形状 (n_texts, dim)。"""
        raise NotImplementedError

    @property
    @abstractmethod
    def dimension(self) -> int:
        """向量维度。"""
        raise NotImplementedError


class MockEmbeddingProvider(EmbeddingProvider):
    """用于测试和无 embedding 环境的伪提供者，生成确定性随机向量。"""

    def __init__(self, dimension: int = 384, seed: int = 42):
        self._dimension = dimension
        self._rng = np.random.default_rng(seed)

    def embed(self, texts: List[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            # 使用文本哈希作为确定性种子，保证相同文本得到相同向量
            seed = hash(text) & 0xFFFFFFFF
            rng = np.random.default_rng(seed)
            vec = rng.normal(size=self._dimension).astype(np.float32)
            vec = vec / (np.linalg.norm(vec) + 1e-8)
            vectors.append(vec)
        return np.array(vectors, dtype=np.float32)

    @property
    def dimension(self) -> int:
        return self._dimension


class OpenAIEmbeddingProvider(EmbeddingProvider):
    """基于 OpenAI API 的 embedding 提供者。"""

    def __init__(self, config: MemoryConfig, api_key: str = "", base_url: Optional[str] = None):
        self.config = config
        self.api_key = api_key
        self.base_url = base_url
        self._client = None
        self._dimension: Optional[int] = None

    def _get_client(self):
        if self._client is None:
            try:
                import openai
            except ImportError as exc:
                raise ImportError("openai package is required for OpenAI embedding") from exc
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            self._client = openai.OpenAI(**client_kwargs)
        return self._client

    def embed(self, texts: List[str]) -> np.ndarray:
        client = self._get_client()
        response = client.embeddings.create(input=texts, model=self.config.model)
        vectors = np.array([item.embedding for item in response.data], dtype=np.float32)
        if self._dimension is None and vectors.size:
            self._dimension = vectors.shape[1]
        return vectors

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            sample = self.embed(["sample"])
            self._dimension = sample.shape[1]
        return self._dimension


class SentenceTransformerProvider(EmbeddingProvider):
    """基于 sentence-transformers 的本地 embedding 提供者。"""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._dimension: Optional[int] = None

    def _get_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required. Install with: pip install sentence-transformers"
                ) from exc
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed(self, texts: List[str]) -> np.ndarray:
        model = self._get_model()
        vectors = model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)
        if isinstance(vectors, list):
            vectors = np.array(vectors, dtype=np.float32)
        if self._dimension is None and vectors.size:
            self._dimension = vectors.shape[1]
        return vectors.astype(np.float32)

    @property
    def dimension(self) -> int:
        if self._dimension is None:
            sample = self.embed(["sample"])
            self._dimension = sample.shape[1]
        return self._dimension


def build_embedding_provider(config: MemoryConfig, api_key: str = "", base_url: Optional[str] = None) -> EmbeddingProvider:
    """根据配置构建 embedding 提供者。"""
    if config.backend == "mock":
        return MockEmbeddingProvider()
    if config.backend == "openai":
        return OpenAIEmbeddingProvider(config, api_key=api_key, base_url=base_url)
    if config.backend == "sentence_transformers":
        return SentenceTransformerProvider(model_name=config.model)
    raise ValueError(f"Unsupported embedding backend: {config.backend}")


def build_report_text(report: Report) -> str:
    """将报告拼接为用于 embedding 的文本。"""
    parts = [f"标题：{report.title}", f"主题：{report.topic}"]
    if report.findings:
        parts.append("发现：" + " ".join(f.text for f in report.findings[:20]))
    if report.entities:
        parts.append("实体：" + " ".join(e.name for e in report.entities[:30]))
    if report.topics:
        parts.append("主题：" + " ".join(t.name for t in report.topics[:30]))
    return "\n".join(parts)


class VectorMemory:
    """基于 numpy 文件的轻量级向量存储。"""

    def __init__(self, vector_dir: str = "vectors"):
        self.vector_dir = Path(vector_dir)
        self.vector_dir.mkdir(parents=True, exist_ok=True)
        self.vectors_file = self.vector_dir / "vectors.npy"
        self.meta_file = self.vector_dir / "metadata.jsonl"

        self._report_ids: List[str] = []
        self._vectors: Optional[np.ndarray] = None
        self._load()

    def _load(self):
        if self.vectors_file.exists() and self.meta_file.exists():
            try:
                self._vectors = np.load(str(self.vectors_file))
                self._report_ids = []
                with self.meta_file.open("r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._report_ids.append(json.loads(line)["report_id"])
                logger.info("已加载 %d 条向量记忆", len(self._report_ids))
            except Exception as exc:
                logger.warning("加载向量记忆失败: %s", exc)
                self._vectors = None
                self._report_ids = []

    def _save(self):
        if self._vectors is not None:
            np.save(str(self.vectors_file), self._vectors)
        with self.meta_file.open("w", encoding="utf-8") as f:
            for rid in self._report_ids:
                f.write(json.dumps({"report_id": rid}, ensure_ascii=False) + "\n")

    def add(self, report_id: str, vector: np.ndarray) -> None:
        """添加或更新报告向量。"""
        vector = vector.reshape(1, -1).astype(np.float32)
        if report_id in self._report_ids:
            idx = self._report_ids.index(report_id)
            if self._vectors is not None:
                self._vectors[idx] = vector[0]
        else:
            self._report_ids.append(report_id)
            if self._vectors is None:
                self._vectors = vector
            else:
                self._vectors = np.vstack([self._vectors, vector])
        self._save()

    def remove(self, report_id: str) -> bool:
        """删除报告向量。"""
        if report_id not in self._report_ids:
            return False
        idx = self._report_ids.index(report_id)
        del self._report_ids[idx]
        if self._vectors is not None:
            self._vectors = np.delete(self._vectors, idx, axis=0)
        self._save()
        return True

    def search(
        self,
        query_vector: np.ndarray,
        top_k: int = 10,
        exclude_ids: Optional[List[str]] = None,
    ) -> List[Tuple[str, float]]:
        """基于余弦相似度检索最相关的报告 ID。"""
        if self._vectors is None or len(self._vectors) == 0:
            return []
        query_vector = query_vector.reshape(-1).astype(np.float32)
        query_norm = np.linalg.norm(query_vector)
        if query_norm == 0:
            return []
        query_vector = query_vector / query_norm

        norms = np.linalg.norm(self._vectors, axis=1)
        similarities = self._vectors @ query_vector / (norms + 1e-8)

        exclude_set = set(exclude_ids or [])
        indexed_sims = [
            (i, float(sim))
            for i, sim in enumerate(similarities)
            if self._report_ids[i] not in exclude_set
        ]
        indexed_sims.sort(key=lambda x: x[1], reverse=True)

        return [(self._report_ids[i], sim) for i, sim in indexed_sims[:top_k]]

    def clear(self):
        """清空向量记忆。"""
        self._report_ids = []
        self._vectors = None
        if self.vectors_file.exists():
            self.vectors_file.unlink()
        if self.meta_file.exists():
            self.meta_file.unlink()

    def list_ids(self) -> List[str]:
        return list(self._report_ids)
