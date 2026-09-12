"""Tests for Phase 4: Semantic matching engine using Sentence Transformers."""

from __future__ import annotations

import pytest

from app.matching.semantic_matcher import (
    build_jd_requirements,
    build_resume_evidence,
    compute_requirement_similarities,
    compute_semantic_details,
    compute_semantic_score,
    get_embedding_model,
)
from app.models.jd_models import JobDescription
from app.models.resume_models import Experience, Project, Resume


@pytest.fixture(scope="module")
def embedding_model():
    """Module-scoped embedding model to share across tests."""
    return get_embedding_model()


class TestSemanticMatching:
    """Test suite for semantic similarity matching."""

    # -----------------------------------------------------------------------
    # Test A & B: Related vs Unrelated semantic wording
    # -----------------------------------------------------------------------
    def test_related_vs_unrelated_wording(self, embedding_model):
        """Semantically related phrasing scores significantly higher than unrelated phrasing."""
        jd = JobDescription(
            responsibilities=["Develop REST APIs using Node.js."],
        )

        # Related resume: Express, web services, HTTP endpoints (no exact match with Node.js in wording)
        resume_related = Resume(
            projects=[
                Project(
                    name="API Service",
                    description="Built backend web services with Express and HTTP endpoints.",
                )
            ]
        )

        # Unrelated resume: Mechanical CAD engineering
        resume_unrelated = Resume(
            experience=[
                Experience(
                    role="CAD Designer",
                    description="Designed mechanical components using CAD software and 3D printing.",
                )
            ]
        )

        score_related = compute_semantic_score(jd, resume_related, model=embedding_model)
        score_unrelated = compute_semantic_score(jd, resume_unrelated, model=embedding_model)

        assert score_related > score_unrelated
        # Related score should be comfortably above baseline and unrelated should be low
        assert score_related >= 40.0
        assert score_unrelated < 25.0

    # -----------------------------------------------------------------------
    # Test C: Multiple evidence chunks selects the best match
    # -----------------------------------------------------------------------
    def test_selects_best_relevant_evidence(self, embedding_model):
        """When multiple chunks are available, the requirement selects the best matching evidence."""
        jd = JobDescription(
            required_skills=["MongoDB database design"],
        )

        resume = Resume(
            projects=[
                Project(
                    name="Financial Ledger",
                    description="Accounting and financial ledger bookkeeping for business expenses.",
                ),
                Project(
                    name="Data Pipeline",
                    description="Implemented database schema, indexing, and aggregation pipelines in MongoDB.",
                ),
                Project(
                    name="Bash Scripting",
                    description="Wrote basic shell scripts for file backups.",
                ),
            ]
        )

        matches = compute_requirement_similarities(jd, resume, model=embedding_model)

        assert len(matches) == 1
        best_match = matches[0]
        # Should pick the MongoDB data pipeline, not the financial ledger or bash script
        assert "MongoDB" in best_match["best_matching_evidence"]
        assert "Data Pipeline" in best_match["best_matching_evidence"]
        assert best_match["similarity_score"] > 60.0

    # -----------------------------------------------------------------------
    # Test D: Empty inputs handle gracefully without crashing
    # -----------------------------------------------------------------------
    def test_empty_requirements(self, embedding_model):
        """Empty JD requirements returns score 0.0 and empty matches."""
        jd = JobDescription(required_skills=[], preferred_skills=[], responsibilities=[])
        resume = Resume(skills=["Python", "FastAPI"])

        matches = compute_requirement_similarities(jd, resume, model=embedding_model)
        score = compute_semantic_score(jd, resume, model=embedding_model)

        assert matches == []
        assert score == 0.0

    def test_empty_resume_evidence(self, embedding_model):
        """Empty resume evidence returns 0.0 score without division by zero."""
        jd = JobDescription(required_skills=["Python", "FastAPI"])
        resume = Resume(skills=[], projects=[], experience=[], education=[])

        matches = compute_requirement_similarities(jd, resume, model=embedding_model)
        score = compute_semantic_score(jd, resume, model=embedding_model)

        assert len(matches) == 2
        for m in matches:
            assert m["similarity"] == 0.0
            assert m["best_matching_evidence"] == ""
        assert score == 0.0

    def test_both_empty(self, embedding_model):
        """Both JD and Resume empty returns 0.0."""
        jd = JobDescription()
        resume = Resume()

        score = compute_semantic_score(jd, resume, model=embedding_model)
        assert score == 0.0

    # -----------------------------------------------------------------------
    # Test E: Deterministic behavior / stability
    # -----------------------------------------------------------------------
    def test_deterministic_output(self, embedding_model):
        """Repeated evaluations on identical inputs produce identical scores."""
        jd = JobDescription(
            required_skills=["React", "Node.js"],
            responsibilities=["Build high-throughput web applications."],
        )
        resume = Resume(
            skills=["React", "TypeScript"],
            projects=[
                Project(name="Web App", description="Constructed high performance web app with React."),
            ],
        )

        score_1 = compute_semantic_score(jd, resume, model=embedding_model)
        score_2 = compute_semantic_score(jd, resume, model=embedding_model)

        assert score_1 == score_2

    # -----------------------------------------------------------------------
    # Test F: Building JD requirements and resume evidence
    # -----------------------------------------------------------------------
    def test_build_jd_requirements(self):
        """JD requirements combines responsibilities, skills, and qualifications."""
        jd = JobDescription(
            required_skills=["Python", "Docker"],
            responsibilities=["Lead backend architecture development."],
            qualifications=["B.S. in Computer Science"],
            preferred_skills=["Kubernetes"],
        )

        reqs = build_jd_requirements(jd)

        assert any("Lead backend architecture" in r for r in reqs)
        assert any("Python" in r for r in reqs)
        assert any("B.S. in Computer Science" in r for r in reqs)
        assert any("Kubernetes" in r for r in reqs)

    def test_build_resume_evidence(self):
        """Resume evidence captures natural language project and experience details."""
        resume = Resume(
            skills=["Python", "Docker"],
            experience=[
                Experience(
                    role="Software Engineer",
                    company="Acme Corp",
                    duration="2022 - 2024",
                    description="Engineered microservices and deployed container clusters.",
                )
            ],
            projects=[
                Project(
                    name="Stream Platform",
                    technologies=["Python", "Kafka"],
                    description="Built event-driven stream ingestion.",
                )
            ],
        )

        evidence = build_resume_evidence(resume)

        assert any("Engineered microservices" in ev for ev in evidence)
        assert any("Stream Platform" in ev for ev in evidence)
        assert any("Technical Skills" in ev for ev in evidence)

    # -----------------------------------------------------------------------
    # Test G: compute_semantic_details structure
    # -----------------------------------------------------------------------
    def test_compute_semantic_details(self, embedding_model):
        """compute_semantic_details returns both score and requirement-level matches."""
        jd = JobDescription(required_skills=["React"], responsibilities=["Build web UIs."])
        resume = Resume(projects=[Project(name="UI", description="Built frontend user interfaces with React.")])

        details = compute_semantic_details(jd, resume, model=embedding_model)

        assert "semantic_score" in details
        assert "requirement_matches" in details
        assert 0.0 <= details["semantic_score"] <= 100.0
        assert len(details["requirement_matches"]) == 2
        for match in details["requirement_matches"]:
            assert "requirement" in match
            assert "best_matching_evidence" in match
            assert "similarity" in match
            assert "similarity_score" in match
            assert 0.0 <= match["similarity"] <= 1.0
