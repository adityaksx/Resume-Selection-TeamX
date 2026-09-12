"""Tests for Phase 5: Final scoring, candidate ranking, and tie-breaking (plan.md §13, §14)."""

from __future__ import annotations

import pytest

from app.matching.pipeline import score_candidate, shortlist_candidates
from app.matching.scorer import compute_final_score, rank_candidates
from app.matching.semantic_matcher import get_embedding_model
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult
from app.models.resume_models import Project, Resume


@pytest.fixture(scope="module")
def embedding_model():
    """Module-scoped embedding model for integration tests."""
    return get_embedding_model()


class TestFinalScoring:
    """Tests for compute_final_score()."""

    def test_scenario_a_equal_components(self):
        """keyword = 80, semantic = 80 -> final = 80."""
        assert compute_final_score(80.0, 80.0) == 80.0

    def test_scenario_b_different_components(self):
        """keyword = 80, semantic = 90 -> final = 85 (0.50 * 80 + 0.50 * 90)."""
        assert compute_final_score(80.0, 90.0) == 85.0

    def test_scenario_c_boundary_values(self):
        """0 + 0 -> 0, 100 + 100 -> 100, clamping out-of-range inputs."""
        assert compute_final_score(0.0, 0.0) == 0.0
        assert compute_final_score(100.0, 100.0) == 100.0
        # Clamping check
        assert compute_final_score(-10.0, 50.0) == 25.0
        assert compute_final_score(50.0, 150.0) == 75.0

    def test_scenario_d_both_components_affect_score(self):
        """Score integrity: changing either component genuinely affects the final score."""
        base = compute_final_score(80.0, 80.0)
        assert base == 80.0

        # Changing keyword only
        higher_kw = compute_final_score(100.0, 80.0)
        assert higher_kw == 90.0
        assert higher_kw > base

        # Changing semantic only
        higher_sem = compute_final_score(80.0, 100.0)
        assert higher_sem == 90.0
        assert higher_sem > base


class TestRankingAndTieBreaking:
    """Tests for rank_candidates() and deterministic tie-breaking."""

    def test_ranking_descending_by_final_score(self):
        """Candidates are sorted descending by final score."""
        c1 = CandidateResult(candidate_name="Alice", final_score=75.0, keyword_score=70.0, semantic_score=80.0)
        c2 = CandidateResult(candidate_name="Bob", final_score=92.0, keyword_score=90.0, semantic_score=94.0)
        c3 = CandidateResult(candidate_name="Charlie", final_score=60.0, keyword_score=60.0, semantic_score=60.0)

        result = rank_candidates([c1, c2, c3], jd_role_title="Software Engineer")

        assert isinstance(result, RankingResult)
        assert len(result.candidates) == 3
        assert [c.candidate_name for c in result.candidates] == ["Bob", "Alice", "Charlie"]
        assert [c.rank for c in result.candidates] == [1, 2, 3]

    def test_tie_breaking_keyword_score(self):
        """When final scores are equal, candidate with higher keyword score ranks higher."""
        # Both have final score = 85.0
        # Alice: kw=90, sem=80
        # Bob: kw=80, sem=90
        c_alice = CandidateResult(candidate_name="Alice", final_score=85.0, keyword_score=90.0, semantic_score=80.0)
        c_bob = CandidateResult(candidate_name="Bob", final_score=85.0, keyword_score=80.0, semantic_score=90.0)

        result = rank_candidates([c_bob, c_alice])

        assert result.candidates[0].candidate_name == "Alice"
        assert result.candidates[1].candidate_name == "Bob"

    def test_tie_breaking_matched_required_count(self):
        """When final score and keyword score tie, higher count of matched required skills wins."""
        # Both final = 80.0, keyword = 80.0
        c1 = CandidateResult(
            candidate_name="David",
            final_score=80.0,
            keyword_score=80.0,
            matched_required_skills=["React", "Node.js", "MongoDB"],  # 3 skills
        )
        c2 = CandidateResult(
            candidate_name="Daniel",
            final_score=80.0,
            keyword_score=80.0,
            matched_required_skills=["React", "Node.js"],  # 2 skills
        )

        result = rank_candidates([c2, c1])

        assert result.candidates[0].candidate_name == "David"
        assert result.candidates[1].candidate_name == "Daniel"

    def test_tie_breaking_alphabetical_name(self):
        """When all scores and counts tie, alphabetical order by candidate_name is the final tie-breaker."""
        c_zack = CandidateResult(
            candidate_name="Zack",
            final_score=80.0,
            keyword_score=80.0,
            matched_required_skills=["React"],
        )
        c_adam = CandidateResult(
            candidate_name="Adam",
            final_score=80.0,
            keyword_score=80.0,
            matched_required_skills=["React"],
        )

        result = rank_candidates([c_zack, c_adam])

        assert result.candidates[0].candidate_name == "Adam"
        assert result.candidates[1].candidate_name == "Zack"

    def test_empty_candidate_list(self):
        """Empty candidate list returns empty RankingResult."""
        result = rank_candidates([], jd_role_title="None")
        assert result.candidates == []
        assert result.top_3 == []


class TestPipelineIntegration:
    """End-to-end pipeline test across synthetic JD and multiple resumes."""

    def test_end_to_end_shortlist_pipeline(self, embedding_model):
        """Orchestrates JD + 4 synthetic resumes from extraction through final ranking."""
        jd = JobDescription(
            role_title="Full Stack Developer Intern",
            required_skills=["React", "Node.js", "MongoDB"],
            preferred_skills=["Docker", "TypeScript"],
            responsibilities=[
                "Develop scalable backend REST APIs using Node.js and Express.",
                "Build responsive web user interfaces with React.",
            ],
        )

        # 4 Candidates with varying degrees of fit
        # Strong match: matches required skills + relevant project
        r1 = Resume(
            candidate_name="Candidate Strong",
            skills=["React", "Node.js", "MongoDB", "TypeScript"],
            projects=[
                Project(
                    name="Fullstack Portal",
                    technologies=["React", "Node.js", "MongoDB"],
                    description="Developed scalable backend REST APIs using Node.js and built React frontend.",
                )
            ],
        )

        # Moderate match: partial required skills + partial semantic
        r2 = Resume(
            candidate_name="Candidate Moderate",
            skills=["React", "Docker"],
            projects=[
                Project(
                    name="Frontend Site",
                    technologies=["React"],
                    description="Built personal portfolio with React components.",
                )
            ],
        )

        # Weak match: different domain
        r3 = Resume(
            candidate_name="Candidate Weak",
            skills=["Python", "SQL"],
            projects=[
                Project(
                    name="Data Script",
                    description="Automated report generation using Python and SQL queries.",
                )
            ],
        )

        # Non-matching candidate
        r4 = Resume(
            candidate_name="Candidate Mismatch",
            skills=["Photoshop", "Illustrator"],
            projects=[
                Project(
                    name="Graphic Design",
                    description="Created marketing brochures and vector illustrations in Photoshop.",
                )
            ],
        )

        resumes = {
            "cand_strong.pdf": r1,
            "cand_moderate.pdf": r2,
            "cand_weak.pdf": r3,
            "cand_mismatch.pdf": r4,
        }

        ranking = shortlist_candidates(jd, resumes, model=embedding_model)

        # Assertions
        assert isinstance(ranking, RankingResult)
        assert len(ranking.candidates) == 4

        # Every candidate appears in ranking with rank 1..4
        assert [c.rank for c in ranking.candidates] == [1, 2, 3, 4]

        # Ranking is descending by final_score
        scores = [c.final_score for c in ranking.candidates]
        assert scores == sorted(scores, reverse=True)

        # Strong candidate should rank #1
        top_cand = ranking.candidates[0]
        assert top_cand.candidate_name == "Candidate Strong"
        assert top_cand.rank == 1
        assert top_cand.filename == "cand_strong.pdf"

        # Check score math for top candidate
        expected_final = round(0.50 * top_cand.keyword_score + 0.50 * top_cand.semantic_score, 2)
        assert top_cand.final_score == expected_final

        # Check evidence preservation
        assert len(top_cand.semantic_evidence) > 0
        for ev in top_cand.semantic_evidence:
            assert "requirement" in ev
            assert "best_matching_evidence" in ev
            assert "similarity" in ev

        # All scores bounded 0..100
        for c in ranking.candidates:
            assert 0.0 <= c.keyword_score <= 100.0
            assert 0.0 <= c.semantic_score <= 100.0
            assert 0.0 <= c.final_score <= 100.0
