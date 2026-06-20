"""可信验证与溯源系统单元测试。"""

import pytest

from agent.config import LLMConfig
from agent.research_state import PageSummary, ResearchState
from agent.verification import ResearchVerifier
from agent.verification.claim_extractor import ClaimExtractor
from agent.verification.confidence_scorer import ConfidenceScorer
from agent.verification.cross_validator import CrossValidator
from agent.verification.evidence_collector import EvidenceCollector
from agent.verification.hallucination_detector import HallucinationDetector
from agent.verification.models import (
    Claim,
    Evidence,
    EvidenceChain,
    EvidenceStance,
    VerificationVerdict,
)
from agent.verification.traceability_engine import TraceabilityEngine


@pytest.fixture
def fake_llm_config():
    return LLMConfig(api_key="fake-key", base_url="http://localhost/v1", model="fake")


@pytest.fixture
def sample_state():
    state = ResearchState()
    state.add_source(
        title="AI in Medical Imaging",
        url="http://example.com/ai-medical",
    )
    state.add_source(
        title="Radiology AI Survey",
        url="http://survey.org/radiology-ai",
    )
    state.add_summary(
        PageSummary(
            source_index=1,
            url="http://example.com/ai-medical",
            title="AI in Medical Imaging",
            summary="Artificial intelligence improves radiology accuracy significantly.",
            key_findings=["AI improves radiology accuracy.", "Deep learning detects tumors."],
            entities=["Google Health", "DeepMind"],
            relevance_score=8,
        )
    )
    state.add_summary(
        PageSummary(
            source_index=2,
            url="http://survey.org/radiology-ai",
            title="Radiology AI Survey",
            summary="Multiple studies confirm AI improves radiology accuracy and reduces error rates.",
            key_findings=["AI improves radiology accuracy.", "Error rates drop with AI."],
            entities=["Radiology", "AI"],
            relevance_score=9,
        )
    )
    state.findings = [
        "AI improves radiology accuracy.",
        "Deep learning detects tumors.",
    ]
    return state


def test_claim_extractor_from_findings(fake_llm_config, sample_state):
    extractor = ClaimExtractor(fake_llm_config)
    claims = extractor.extract_claims(sample_state, max_claims=5, language="en")
    assert len(claims) == 2
    assert claims[0].text == "AI improves radiology accuracy."


def test_evidence_collector(sample_state):
    collector = EvidenceCollector()
    claim = Claim(id="c1", text="AI improves radiology accuracy.")
    evidence_map = collector.collect(sample_state, [claim])
    evidences = evidence_map[claim.id]
    assert len(evidences) == 2
    assert all(e.stance == EvidenceStance.SUPPORT for e in evidences)
    assert any(e.is_direct_quote for e in evidences)
    assert {e.source_index for e in evidences} == {1, 2}


def test_cross_validator(sample_state):
    validator = CrossValidator()
    evidences = [
        Evidence(
            source_index=1,
            url="http://example.com/ai-medical",
            title="AI in Medical Imaging",
            quote="AI improves radiology accuracy.",
            stance=EvidenceStance.SUPPORT,
            relevance_score=8,
            domain="example.com",
        ),
        Evidence(
            source_index=2,
            url="http://survey.org/radiology-ai",
            title="Radiology AI Survey",
            quote="Studies confirm AI improves radiology accuracy.",
            stance=EvidenceStance.SUPPORT,
            relevance_score=9,
            domain="survey.org",
        ),
    ]
    signals = validator.validate(sample_state, evidences)
    assert signals["supporting_count"] == 2
    assert signals["unique_domain_count"] == 2
    assert signals["agreement_ratio"] == 1.0


def test_confidence_scorer_verified():
    scorer = ConfidenceScorer()
    signals = {
        "supporting_count": 3,
        "refuting_count": 0,
        "unique_domain_count": 3,
        "agreement_ratio": 1.0,
        "direct_quote_count": 2,
        "average_relevance": 8.0,
    }
    result = scorer.score(signals)
    assert result["score"] >= 80
    assert result["verdict"] == VerificationVerdict.VERIFIED
    assert result["label"] == "已验证"


def test_confidence_scorer_refuted():
    scorer = ConfidenceScorer()
    signals = {
        "supporting_count": 1,
        "refuting_count": 3,
        "unique_domain_count": 2,
        "agreement_ratio": 0.25,
        "direct_quote_count": 1,
        "average_relevance": 6.0,
    }
    result = scorer.score(signals)
    assert result["verdict"] == VerificationVerdict.REFUTED
    assert result["label"] == "被反驳"
    assert result["score"] < 40


def test_hallucination_detector():
    detector = HallucinationDetector()
    report = (
        "AI improves radiology accuracy. "
        "The market size will reach 50 billion dollars in 2030. "
        "Deep learning detects tumors effectively."
    )
    chains = [
        EvidenceChain(
            claim=Claim(id="c1", text="AI improves radiology accuracy."),
            verdict=VerificationVerdict.VERIFIED,
            confidence_score=85,
        ),
        EvidenceChain(
            claim=Claim(id="c2", text="Deep learning detects tumors effectively."),
            verdict=VerificationVerdict.PLAUSIBLE,
            confidence_score=70,
        ),
    ]
    result = detector.detect(report, chains)
    assert result["flagged_count"] >= 1
    assert any("50 billion" in f["sentence"] for f in result["flagged_sentences"])
    assert result["risk_score"] > 0


def test_traceability_engine_render():
    engine = TraceabilityEngine()
    claim = Claim(id="c1", text="AI improves radiology accuracy.")
    evidence = Evidence(
        source_index=1,
        url="http://example.com/ai-medical",
        title="AI in Medical Imaging",
        quote="AI improves radiology accuracy significantly.",
        stance=EvidenceStance.SUPPORT,
        relevance_score=9,
        domain="example.com",
    )
    chain = engine.build_chain(
        claim=claim,
        evidences=[evidence],
        score_result={
            "score": 85,
            "label": "已验证",
            "verdict": VerificationVerdict.VERIFIED,
            "concerns": [],
        },
        signals={
            "supporting_count": 1,
            "refuting_count": 0,
            "support_domains": ["example.com"],
            "unique_domain_count": 1,
            "direct_quote_count": 1,
            "average_relevance": 9.0,
        },
    )
    hallucination = {"risk_score": 0.1, "flagged_sentences": []}
    markdown = engine.render_markdown([chain], hallucination, language="zh")
    assert "证据链与可信度附录" in markdown
    assert "已验证" in markdown
    assert "http://example.com/ai-medical" in markdown


def test_research_verifier_integration(fake_llm_config, sample_state):
    sample_state.report_body = ""
    verifier = ResearchVerifier(fake_llm_config, max_claims=5)
    chains, hallucination, report = verifier.verify(sample_state, language="en")
    assert len(chains) >= 1
    assert isinstance(report, str)
    assert "Evidence Chain" in report or "证据链" in report


def test_research_verifier_finds_refutation(fake_llm_config):
    state = ResearchState()
    state.add_source(title="Myths about AI", url="http://myths.example.com/ai")
    state.add_summary(
        PageSummary(
            source_index=1,
            url="http://myths.example.com/ai",
            title="Myths about AI",
            summary="Recent claims that AI improves radiology accuracy are not supported by evidence.",
            key_findings=["AI does not improve radiology accuracy."],
            relevance_score=7,
        )
    )
    state.findings = ["AI improves radiology accuracy."]
    verifier = ResearchVerifier(fake_llm_config, max_claims=5)
    chains, _, _ = verifier.verify(state, language="en")
    assert any(c.verdict == VerificationVerdict.REFUTED for c in chains)
