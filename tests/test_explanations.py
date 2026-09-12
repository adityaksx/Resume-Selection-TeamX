"""Tests for Phase 6: Top-3 Explainable Shortlist (plan.md §15).

Verifies deterministic, rule-based explanation generation grounded strictly in stored evidence,
with zero generative LLM or API dependencies.
"""

from __future__ import annotations

import pytest

from app.explanation.explanation_generator import (
    attach_top_explanations,
    generate_candidate_explanation,
    select_top_semantic_evidence,
)
from app.models.result_models import CandidateResult, RankingResult


class TestExplanationGenerator:
    """Test suite for deterministic explanation generation."""

    def test_scenario_a_strong_candidate(self):
        """A. Strong candidate: Verify explanation contains name, scores, matched skills, semantic evidence."""
        cand = CandidateResult(
            candidate_name="Rahul Sharma",
            rank=1,
            final_score=91.42,
            keyword_score=89.00,
            semantic_score=93.84,
            matched_required_skills=["React", "Node.js", "MongoDB", "REST API", "Git"],
            missing_required_skills=[],
            matched_preferred_skills=["Docker"],
            missing_preferred_skills=["TypeScript"],
            semantic_evidence=[
                {
                    "requirement": "Develop REST APIs using Node.js",
                    "best_matching_evidence": "Built backend services using Express and HTTP endpoints.",
                    "similarity": 0.864,
                    "similarity_score": 86.4,
                },
                {
                    "requirement": "Build responsive frontend interfaces with React",
                    "best_matching_evidence": "Designed reusable component library using React and CSS.",
                    "similarity": 0.821,
                    "similarity_score": 82.1,
                },
            ],
        )

        explanation = generate_candidate_explanation(cand)

        # 1. Header & scores present
        assert "Candidate: Rahul Sharma" in explanation
        assert "91.42" in explanation
        assert "89.00" in explanation
        assert "93.84" in explanation

        # 2. Matched required skills present
        for skill in ["React", "Node.js", "MongoDB", "REST API", "Git"]:
            assert skill in explanation

        # 3. Preferred skills present
        assert "Docker" in explanation
        assert "TypeScript" in explanation

        # 4. Semantic evidence present
        assert "Develop REST APIs using Node.js" in explanation
        assert "Built backend services using Express" in explanation
        assert "86.4%" in explanation

    def test_scenario_b_missing_required_skills(self):
        """B. Missing required skills: Missing skills are explicitly highlighted."""
        cand = CandidateResult(
            candidate_name="Alex Rivera",
            rank=2,
            final_score=72.50,
            keyword_score=60.00,
            semantic_score=85.00,
            matched_required_skills=["React", "Git"],
            missing_required_skills=["MongoDB", "REST API", "Node.js"],
            matched_preferred_skills=[],
            missing_preferred_skills=["Docker"],
        )

        explanation = generate_candidate_explanation(cand)

        assert "Alex Rivera" in explanation
        assert "Missing required skills:" in explanation
        assert "MongoDB" in explanation
        assert "REST API" in explanation
        assert "Node.js" in explanation

    def test_scenario_c_no_preferred_skills(self):
        """C. No preferred skills: Handled gracefully without crash or missing sections."""
        cand = CandidateResult(
            candidate_name="Jordan Lee",
            rank=3,
            final_score=65.00,
            keyword_score=65.00,
            semantic_score=65.00,
            matched_required_skills=["Python"],
            missing_required_skills=["SQL"],
            matched_preferred_skills=[],
            missing_preferred_skills=[],
            semantic_evidence=[],
        )

        explanation = generate_candidate_explanation(cand)

        assert "Preferred skills matched:" in explanation
        assert "None" in explanation
        assert "Preferred skills missing:" in explanation

    def test_scenario_d_no_semantic_evidence(self):
        """D. No semantic evidence: Clearly states no evidence; does not invent or hallucinate."""
        cand = CandidateResult(
            candidate_name="Taylor Swift",
            rank=1,
            final_score=80.00,
            keyword_score=80.00,
            semantic_score=80.00,
            matched_required_skills=["Swift", "iOS"],
            missing_required_skills=[],
            semantic_evidence=[],
        )

        explanation = generate_candidate_explanation(cand)

        assert "Strong semantic evidence:" in explanation
        assert "No strong semantic evidence recorded." in explanation

    def test_scenario_e_top_3_only(self):
        """E. Top-3 only: Only candidates ranked 1-3 receive full explanations; 4-5 do not."""
        cands = [
            CandidateResult(candidate_name=f"Candidate {i}", rank=i, final_score=100.0 - (i * 10))
            for i in range(1, 6)  # 5 candidates
        ]
        ranking = RankingResult(candidates=cands)

        updated_ranking = attach_top_explanations(ranking, top_k=3)

        assert len(updated_ranking.candidates) == 5

        # Ranks 1-3 have populated explanations
        for c in updated_ranking.candidates[:3]:
            assert c.explanation is not None
            assert len(c.explanation) > 50
            assert c.candidate_name in c.explanation

        # Ranks 4-5 do NOT receive full explanations
        for c in updated_ranking.candidates[3:]:
            assert c.explanation is None

    def test_scenario_f_grounding_no_hallucinations(self):
        """F. Grounding: Explanation only contains factual info from CandidateResult."""
        cand = CandidateResult(
            candidate_name="Elena Rostov",
            rank=1,
            final_score=88.50,
            keyword_score=90.00,
            semantic_score=87.00,
            matched_required_skills=["Go", "Kubernetes"],
            missing_required_skills=["Terraform"],
            matched_preferred_skills=[],
            missing_preferred_skills=[],
            semantic_evidence=[
                {
                    "requirement": "Experience deploying on Kubernetes",
                    "best_matching_evidence": "Configured Helm charts and deployed microservices on EKS.",
                    "similarity": 0.88,
                    "similarity_score": 88.0,
                }
            ],
        )

        explanation = generate_candidate_explanation(cand)

        # Confirm strict grounding
        assert "Elena Rostov" in explanation
        assert "Go" in explanation
        assert "Kubernetes" in explanation
        assert "Terraform" in explanation
        assert "Configured Helm charts" in explanation

        # Ensure no ungrounded fluff / buzzwords
        lower_exp = explanation.lower()
        assert "perfect candidate" not in lower_exp
        assert "guaranteed fit" not in lower_exp
        assert "outstanding candidate" not in lower_exp
        assert "ideal candidate" not in lower_exp

        # Ensure no hallucinated technologies not in candidate data
        assert "react" not in lower_exp
        assert "python" not in lower_exp
        assert "aws" not in lower_exp

    def test_ranking_order_and_scores_preserved(self):
        """attach_top_explanations must not alter candidate order, scores, or rankings."""
        c1 = CandidateResult(candidate_name="Alpha", rank=1, final_score=95.0, keyword_score=90.0, semantic_score=100.0)
        c2 = CandidateResult(candidate_name="Beta", rank=2, final_score=85.0, keyword_score=80.0, semantic_score=90.0)
        c3 = CandidateResult(candidate_name="Gamma", rank=3, final_score=75.0, keyword_score=70.0, semantic_score=80.0)
        c4 = CandidateResult(candidate_name="Delta", rank=4, final_score=65.0, keyword_score=60.0, semantic_score=70.0)

        ranking = RankingResult(candidates=[c1, c2, c3, c4])
        result = attach_top_explanations(ranking, top_k=3)

        assert [c.candidate_name for c in result.candidates] == ["Alpha", "Beta", "Gamma", "Delta"]
        assert [c.final_score for c in result.candidates] == [95.0, 85.0, 75.0, 65.0]
        assert [c.rank for c in result.candidates] == [1, 2, 3, 4]


class TestSemanticEvidenceSelection:
    """Test helper for selecting top semantic evidence chunks."""

    def test_filters_low_similarity_and_sorts(self):
        evidence = [
            {"requirement": "Req 1", "best_matching_evidence": "Ev 1", "similarity": 0.45},
            {"requirement": "Req 2", "best_matching_evidence": "Ev 2", "similarity": 0.92},
            {"requirement": "Req 3", "best_matching_evidence": "Ev 3", "similarity": 0.15},
            {"requirement": "Req 4", "best_matching_evidence": "Ev 4", "similarity": 0.78},
        ]
        top = select_top_semantic_evidence(evidence, top_k=2)
        assert len(top) == 2
        assert top[0]["requirement"] == "Req 2"
        assert top[1]["requirement"] == "Req 4"

    def test_handles_empty_evidence(self):
        assert select_top_semantic_evidence([]) == []
