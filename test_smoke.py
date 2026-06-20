"""Smoke test for the deep research agent pipeline without a real LLM."""

from unittest.mock import MagicMock

from agent.config import Config
from agent.llm import LLMClient
from agent.orchestrator import ResearchOrchestrator
from agent.report import generate_report


def test_pipeline():
    cfg = Config.load()
    cfg.llm.api_key = "fake-key"
    cfg.llm.base_url = "http://localhost/v1"
    cfg.llm.model = "fake-model"
    cfg.research.depth = 1
    cfg.research.queries_per_round = 1
    cfg.search.results_per_query = 2
    cfg.search.top_k_to_fetch = 1
    cfg.search.max_workers = 1

    mock_llm = MagicMock(spec=LLMClient)
    mock_llm.generate_search_queries.return_value = ["AI medical diagnosis examples"]
    mock_llm.summarize_page.return_value = {
        "summary": "This page discusses AI in medical imaging.",
        "key_findings": ["AI improves radiology accuracy.", "Deep learning detects tumors."],
        "entities": ["Google Health", "DeepMind"],
        "open_questions": ["What about regulatory approval?"],
        "relevance_score": 8,
    }
    mock_llm.identify_gaps.return_value = ["AI medical diagnosis regulation"]
    mock_llm.find_connections.return_value = {
        "themes": ["Medical imaging", "Regulation"],
        "connections": [{"description": "AI accuracy relates to clinical adoption."}],
        "contradictions": [],
        "gaps": ["Regulatory details"],
    }
    mock_llm.generate_report.return_value = "# Mock Report\n\nThis is a generated report."

    orchestrator = ResearchOrchestrator(cfg)
    orchestrator.llm = mock_llm
    state = orchestrator.run("AI in medical diagnosis")

    assert len(state.sources) >= 1, "Expected at least one source"
    assert len(state.findings) >= 1, "Expected at least one finding"

    report = generate_report("AI in medical diagnosis", state, cfg, mock_llm)
    assert len(report) > 0, "Expected non-empty report"
    assert "参考来源" in report or "Sources" in report, "Expected sources section"

    print("Smoke test passed.")
    print(f"Sources: {len(state.sources)}")
    print(f"Findings: {len(state.findings)}")
    print(f"Entities: {len(state.entities)}")
    print(f"Report length: {len(report)} chars")


if __name__ == "__main__":
    test_pipeline()
