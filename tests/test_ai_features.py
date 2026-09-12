"""Tests for Phase 7B-7G: Server-side Gemini client, Top-3 AI explanations,
Candidate comparison, Improvement advisor, Recruiter AI chat, and JD fairness analysis.
All tests use mocking and do NOT require a live API key.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.llm.client import (
    GeminiError,
    GeminiUnavailableError,
    generate_text,
    get_api_key,
    is_gemini_available,
)
from app.llm.comparison_explainer import (
    explain_comparison_with_ai,
    generate_deterministic_comparison_summary,
)
from app.llm.improvement_advisor import (
    generate_candidate_improvement_advice,
    generate_deterministic_improvement_advice,
)
from app.llm.jd_bias_detector import (
    analyze_jd_fairness,
    run_deterministic_fairness_scan,
)
from app.llm.recruiter_chat import (
    chat_with_recruiter,
    resolve_candidate_references,
)
from app.llm.top3_explainer import (
    attach_top_ai_explanations,
    generate_ai_candidate_explanation,
)
from app.matching.comparator import compare_candidates
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult


@pytest.fixture
def sample_candidate_a():
    return CandidateResult(
        candidate_name="Alice Wang",
        rank=1,
        final_score=85.50,
        keyword_score=90.00,
        semantic_score=81.00,
        matched_required_skills=["React", "Node.js", "MongoDB", "Git"],
        missing_required_skills=["REST API"],
        matched_preferred_skills=["Docker"],
        missing_preferred_skills=["AWS"],
        semantic_evidence=[
            {
                "requirement": "Develop REST APIs with Node.js",
                "best_matching_evidence": "Engineered microservices using Node.js and Express.",
                "similarity": 0.82,
                "similarity_score": 82.0,
            }
        ],
    )


@pytest.fixture
def sample_candidate_b():
    return CandidateResult(
        candidate_name="Bob Smith",
        rank=2,
        final_score=72.00,
        keyword_score=70.00,
        semantic_score=74.00,
        matched_required_skills=["React", "Git"],
        missing_required_skills=["Node.js", "MongoDB", "REST API"],
        matched_preferred_skills=["AWS"],
        missing_preferred_skills=["Docker"],
        semantic_evidence=[],
    )


@pytest.fixture
def sample_jd():
    return JobDescription(
        role_title="Full Stack Developer Intern",
        company="Nexora",
        required_skills=["React", "Node.js", "MongoDB", "REST API", "Git"],
        preferred_skills=["Docker", "AWS"],
        responsibilities=["Develop and scale web applications."],
        qualifications=["Pursuing degree in Computer Science."],
        raw_text="Full Stack Developer Intern. Looking for a ninja rockstar who is young and energetic.",
    )


class TestGeminiClient:
    """Test server-side Gemini client handling and graceful degradation."""

    def test_client_unavailable_without_key(self):
        with patch("app.llm.client.get_api_key", return_value=""):
            assert not is_gemini_available()
            with pytest.raises(GeminiUnavailableError):
                generate_text("Test prompt")

    def test_client_mocked_generation(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_test_key")
        mock_response = MagicMock()
        mock_response.text = "Mocked AI response text."

        with patch("app.llm.client.get_gemini_client") as mock_get_client:
            mock_client = MagicMock()
            mock_client.models.generate_content.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = generate_text("Tell me about candidate A")
            assert result == "Mocked AI response text."
            mock_client.models.generate_content.assert_called_once()


class TestTop3AIExplanation:
    """Test top-3 AI explanation generation and fallback behavior."""

    def test_fallback_when_gemini_unavailable(self, sample_candidate_a, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        with patch("app.llm.client.is_gemini_available", return_value=False):
            explanation = generate_ai_candidate_explanation(sample_candidate_a)
            assert "Alice Wang" in explanation
            assert "85.50" in explanation
            assert "Matched required skills:" in explanation

    def test_ai_explanation_with_mocked_gemini(self, sample_candidate_a, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "fake_key")
        with patch("app.llm.top3_explainer.is_gemini_available", return_value=True):
            with patch("app.llm.top3_explainer.generate_text", return_value="Alice Wang is ranked #1 because of strong Node.js experience."):
                explanation = generate_ai_candidate_explanation(sample_candidate_a)
                assert "Alice Wang is ranked #1" in explanation

    def test_attach_top_ai_explanations_preserves_scores(self, sample_candidate_a, sample_candidate_b):
        ranking = RankingResult(candidates=[sample_candidate_a, sample_candidate_b])
        updated = attach_top_ai_explanations(ranking, top_k=1, force_deterministic=True)

        assert updated.candidates[0].explanation is not None
        assert updated.candidates[1].explanation is None
        # Scores and ranks must be untouched
        assert updated.candidates[0].final_score == sample_candidate_a.final_score
        assert updated.candidates[1].final_score == sample_candidate_b.final_score
        assert updated.candidates[0].rank == 1
        assert updated.candidates[1].rank == 2


class TestCandidateComparison:
    """Test candidate comparison deterministic metrics and AI summary."""

    def test_deterministic_comparison_math(self, sample_candidate_a, sample_candidate_b):
        comp = compare_candidates(sample_candidate_a, sample_candidate_b)
        assert comp.higher_ranked_candidate == "Alice Wang"
        assert comp.final_score_difference == 13.50  # 85.50 - 72.00
        assert comp.keyword_score_difference == 20.00
        assert comp.semantic_score_difference == 7.00
        assert "React" in comp.shared_required_skills
        assert "Node.js" in comp.unique_required_a
        assert "Node.js" in comp.unique_missing_b

    def test_comparison_explanation_fallback(self, sample_candidate_a, sample_candidate_b):
        comp = compare_candidates(sample_candidate_a, sample_candidate_b)
        with patch("app.llm.comparison_explainer.is_gemini_available", return_value=False):
            summary = explain_comparison_with_ai(comp)
            assert "Alice Wang vs Bob Smith" in summary
            assert "Alice Wang" in summary
            assert "13.50" in summary


class TestCandidateImprovementAdvisor:
    """Test candidate improvement recommendations."""

    def test_deterministic_improvement_guidance(self, sample_candidate_a, sample_jd):
        advice = generate_deterministic_improvement_advice(sample_candidate_a, sample_jd)
        assert "Alice Wang" in advice
        # Must note REST API is missing
        assert "REST API" in advice
        assert "Priority Skill Gaps" in advice
        assert "Recommended Next Steps" in advice

    def test_ai_improvement_mocked(self, sample_candidate_a, sample_jd):
        with patch("app.llm.improvement_advisor.is_gemini_available", return_value=True):
            with patch("app.llm.improvement_advisor.generate_text", return_value="1. Priority Skill Gaps\nREST API"):
                advice = generate_candidate_improvement_advice(sample_candidate_a, sample_jd)
                assert "Priority Skill Gaps" in advice


class TestRecruiterAIChat:
    """Test recruiter chat reference resolution and response generation."""

    def test_resolve_candidate_by_name_and_rank(self, sample_candidate_a, sample_candidate_b):
        candidates = [sample_candidate_a, sample_candidate_b]

        # By rank
        res1 = resolve_candidate_references("Why is #1 better than #2?", candidates)
        assert len(res1) == 2
        assert res1[0].candidate_name == "Alice Wang"
        assert res1[1].candidate_name == "Bob Smith"

        # By name
        res2 = resolve_candidate_references("Tell me about Alice", candidates)
        assert len(res2) == 1
        assert res2[0].candidate_name == "Alice Wang"

    def test_chat_fallback_deterministic(self, sample_candidate_a, sample_candidate_b, sample_jd):
        ranking = RankingResult(candidates=[sample_candidate_a, sample_candidate_b])
        with patch("app.llm.recruiter_chat.is_gemini_available", return_value=False):
            ans = chat_with_recruiter("What is Alice missing?", [], ranking, sample_jd)
            assert "Alice Wang is missing" in ans
            assert "REST API" in ans


class TestJDFairnessCheck:
    """Test JD fairness scan for narrow or biased phrasing."""

    def test_deterministic_fairness_scan(self, sample_jd):
        report = run_deterministic_fairness_scan(sample_jd)
        assert len(report.findings) >= 2
        issues = [f.issue for f in report.findings]
        assert "Subjective Phrasing" in issues  # rockstar / ninja
        assert "Age-Coded Language" in issues  # young and energetic
        assert "Potential issue — human review recommended." in report.findings[0].human_review_warning

    def test_ai_fairness_mocked(self, sample_jd):
        mock_json = '{"overall_summary": "Good JD with minor notes", "findings": [{"phrase": "ninja", "issue": "Subjective Phrasing", "rationale": "Vague term", "suggested_alternative": "skilled engineer"}]}'
        with patch("app.llm.jd_bias_detector.is_gemini_available", return_value=True):
            with patch("app.llm.jd_bias_detector.generate_text", return_value=mock_json):
                report = analyze_jd_fairness(sample_jd)
                assert len(report.findings) == 1
                assert report.findings[0].phrase == "ninja"
                assert report.findings[0].suggested_alternative == "skilled engineer"
