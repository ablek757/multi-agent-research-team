"""向量记忆与语义检索测试。"""

import tempfile

import numpy as np

from agent.config import Config, MemoryConfig
from kb import KnowledgeStore, Report
from kb.embeddings import MockEmbeddingProvider, VectorMemory, build_report_text


def test_mock_embedding():
    provider = MockEmbeddingProvider(dimension=8)
    vectors = provider.embed(["a", "b", "a"])
    assert vectors.shape == (3, 8)
    # 相同文本应有相同向量
    assert np.allclose(vectors[0], vectors[2])


def test_vector_memory_add_search():
    memory = VectorMemory(vector_dir=tempfile.mkdtemp())
    vec1 = np.random.rand(8).astype(np.float32)
    vec1 = vec1 / np.linalg.norm(vec1)
    vec2 = np.random.rand(8).astype(np.float32)
    vec2 = vec2 / np.linalg.norm(vec2)

    memory.add("r1", vec1)
    memory.add("r2", vec2)

    results = memory.search(vec1, top_k=2)
    assert results[0][0] == "r1"
    assert len(results) == 2


def test_knowledge_store_with_embedding():
    config = Config.load("config.yaml")
    memory_config = MemoryConfig(enabled=True, backend="mock", vector_dir="vectors")
    with tempfile.TemporaryDirectory() as tmp:
        store = KnowledgeStore(
            data_dir=tmp,
            memory_config=memory_config,
            llm_config=config.llm,
        )
        report = Report(
            id="r1",
            title="量子计算",
            topic="量子计算",
            created_at="2026-01-01T00:00:00",
        )
        store.add_report(report)

        # 语义搜索应能找到自己
        results = store.semantic_search("量子计算", top_k=1)
        assert len(results) == 1
        assert results[0]["report"]["id"] == "r1"


def test_build_report_text():
    report = Report(
        id="r1",
        title="测试报告",
        topic="测试",
        created_at="2026-01-01T00:00:00",
    )
    text = build_report_text(report)
    assert "测试报告" in text
    assert "测试" in text
