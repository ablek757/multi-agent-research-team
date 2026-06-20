"""Smoke test for the multi-agent research team without a real LLM."""

from unittest.mock import MagicMock

from agent.config import Config
from agent.orchestrator import TeamOrchestrator
from agent.report import generate_report
from agent.research_state import PageSummary, Source, VerificationResult


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
    cfg.team.max_research_iterations = 1
    cfg.team.review_rounds = 0

    orchestrator = TeamOrchestrator(cfg)

    # Mock SearchPlanner
    orchestrator.search_planner = MagicMock()
    orchestrator.search_planner.plan_queries.return_value = ["AI medical diagnosis examples"]

    # Mock Researcher: directly inject a source and summary into state
    def fake_research(topic, queries, state):
        source_index = state.add_source(
            title="AI in Medical Imaging",
            url="http://example.com/ai-medical",
        )
        summary = PageSummary(
            source_index=source_index,
            url="http://example.com/ai-medical",
            title="AI in Medical Imaging",
            summary="This page discusses AI in medical imaging.",
            key_findings=["AI improves radiology accuracy.", "Deep learning detects tumors."],
            entities=["Google Health", "DeepMind"],
            open_questions=["What about regulatory approval?"],
            relevance_score=8,
        )
        state.add_summary(summary)

    orchestrator.researcher = MagicMock()
    orchestrator.researcher.research.side_effect = fake_research

    # Mock Analyst
    orchestrator.analyst = MagicMock()

    def fake_analyze(topic, state, language):
        state.themes = ["Medical imaging", "Regulation"]
        state.connections = [{"description": "AI accuracy relates to clinical adoption."}]
        state.contradictions = []
        state.gaps = []

    orchestrator.analyst.analyze.side_effect = fake_analyze

    # Mock FactChecker
    def fake_verify(topic, state, language, max_claims=10):
        state.verification_results = [
            VerificationResult(
                claim="AI improves radiology accuracy.",
                sources=["http://example.com/ai-medical"],
                credibility_score=8,
                assessment="Supported by source.",
                concerns=[],
            )
        ]
        return state.verification_results

    orchestrator.fact_checker = MagicMock()
    orchestrator.fact_checker.verify.side_effect = fake_verify

    # Mock Writer
    orchestrator.writer = MagicMock()
    orchestrator.writer.write.return_value = "# Mock Report\n\nThis is a generated report."
    orchestrator.writer.revise.return_value = "# Mock Report Revised\n\nThis is revised."

    # Mock Editor
    orchestrator.editor = MagicMock()
    orchestrator.editor.review.return_value = "Add more details."

    state = orchestrator.run("AI in medical diagnosis")

    assert len(state.sources) >= 1, "Expected at least one source"
    assert len(state.findings) >= 1, "Expected at least one finding"
    assert len(state.themes) > 0, "Expected analyst to set themes"
    assert len(state.verification_results) > 0, "Expected verification results"
    assert state.report_body, "Expected report body to be generated"

    report = generate_report("AI in medical diagnosis", state, cfg)
    assert len(report) > 0, "Expected non-empty report"
    assert "参考来源" in report or "Sources" in report, "Expected sources section"

    print("Smoke test passed.")
    print(f"Sources: {len(state.sources)}")
    print(f"Findings: {len(state.findings)}")
    print(f"Entities: {len(state.entities)}")
    print(f"Report length: {len(report)} chars")


if __name__ == "__main__":
    test_pipeline()
