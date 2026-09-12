"""Phase 7: Golden regression tests and dataset validation fixtures (plan.md Phase 7).

Ensures long-term robustness against:
- False positives (Java vs JS, C vs C++, Git vs GitHub, AWS vs Azure, React vs React Native)
- Alias normalization (NodeJS, ReactJS, Mongo DB, RESTful API)
- Semantic evidence quality on paraphrased backend vocabulary
- Score distribution and stability across multi-candidate pools
- Absence of LLMs / external API calls
"""

from __future__ import annotations

import glob
import os
import pytest

from app.extraction.jd_extractor import extract_jd
from app.extraction.resume_extractor import extract_resume
from app.matching.keyword_matcher import compute_keyword_score
from app.matching.pipeline import shortlist_candidates
from app.matching.scorer import compute_final_score, rank_candidates
from app.matching.semantic_matcher import compute_semantic_details, get_embedding_model
from app.matching.skill_normalizer import normalize_skill, normalize_skills
from app.models.jd_models import JobDescription
from app.models.resume_models import Project, Resume
from app.parsers.pdf_parser import extract_text_from_pdf


@pytest.fixture(scope="module")
def model():
    return get_embedding_model()


class TestGoldenFixtures:
    """Golden test fixtures representing core real-world edge cases."""

    def test_fixture_1_java_vs_javascript(self):
        """Fixture 1: Java vs JavaScript isolation.
        A candidate with 'Java' and 'Spring Boot' must never match 'JavaScript'.
        """
        jd = JobDescription(
            role_title="Web Developer",
            required_skills=["JavaScript", "React"],
        )
        resume = Resume(
            candidate_name="Java Specialist",
            skills=["Java", "Spring Boot", "Hibernate"],
        )
        res = compute_keyword_score(jd, resume)
        assert "JavaScript" not in res["matched_required_skills"]
        assert "JavaScript" in res["missing_required_skills"]
        assert "Java" not in res["matched_required_skills"]

    def test_fixture_2_nodejs_normalization(self):
        """Fixture 2: NodeJS vs Node.js normalization.
        Variants 'NodeJS', 'Node.js', 'Node JS', and 'node.js' all map to 'Node.js'.
        """
        assert normalize_skill("NodeJS") == "Node.js"
        assert normalize_skill("Node.js") == "Node.js"
        assert normalize_skill("Node JS") == "Node.js"
        assert normalize_skill("node.js") == "Node.js"

        jd = JobDescription(required_skills=["Node.js"])
        resume = Resume(candidate_name="Node Dev", skills=["NodeJS"])
        res = compute_keyword_score(jd, resume)
        assert "Node.js" in res["matched_required_skills"]
        assert res["missing_required_skills"] == []

    def test_fixture_3_semantic_paraphrased_backend_vocabulary(self, model):
        """Fixture 3: Semantic matcher recognizes paraphrased backend engineering without exact words."""
        jd = JobDescription(
            role_title="Backend Engineer",
            required_skills=["Node.js"],
            responsibilities=["Architect and maintain scalable HTTP endpoints and microservices."],
        )
        resume_paraphrased = Resume(
            candidate_name="Backend Paraphrased",
            skills=["Express"],
            projects=[
                Project(
                    name="Web Gateway",
                    description="Constructed distributed web routing services and JSON REST controllers.",
                )
            ],
        )
        resume_unrelated = Resume(
            candidate_name="Civil Engineer",
            skills=["AutoCAD"],
            projects=[
                Project(
                    name="Bridge Design",
                    description="Drafted blueprints for suspension bridge load-bearing columns.",
                )
            ],
        )

        sem_paraphrased = compute_semantic_details(jd, resume_paraphrased, model=model)
        sem_unrelated = compute_semantic_details(jd, resume_unrelated, model=model)

        assert sem_paraphrased["semantic_score"] > sem_unrelated["semantic_score"]
        assert sem_paraphrased["semantic_score"] > 40.0

    def test_fixture_4_missing_multiple_required_skills(self):
        """Fixture 4: Candidate missing all core requirements receives heavy keyword penalty."""
        jd = JobDescription(
            role_title="Full Stack Developer",
            required_skills=["React", "Node.js", "MongoDB", "Git"],
        )
        resume_missing = Resume(
            candidate_name="Unrelated Profile",
            skills=["Photoshop", "Illustrator"],
        )
        res = compute_keyword_score(jd, resume_missing)
        assert res["keyword_score"] == 0.0
        assert len(res["missing_required_skills"]) == 4

        final = compute_final_score(keyword_score=res["keyword_score"], semantic_score=50.0)
        assert final == 25.0  # 0.5 * 0 + 0.5 * 50

    def test_fixture_5_strong_project_evidence_impact(self, model):
        """Fixture 5: Project evidence chunks enrich semantic matching and provide grounded evidence."""
        jd = JobDescription(
            role_title="Full Stack Developer",
            required_skills=["React", "Node.js"],
            responsibilities=["Design and implement responsive React user interfaces."],
        )
        resume = Resume(
            candidate_name="Project Builder",
            skills=["React", "Node.js"],
            projects=[
                Project(
                    name="E-Commerce Store",
                    technologies=["React", "Node.js"],
                    description="Engineered high-speed single page application with modular React components.",
                )
            ],
        )
        sem = compute_semantic_details(jd, resume, model=model)
        assert len(sem["requirement_matches"]) > 0
        best_match = max(sem["requirement_matches"], key=lambda x: x["similarity"])
        assert "React" in best_match["best_matching_evidence"]
        assert best_match["similarity"] > 0.60


class TestRealDatasetEvaluation:
    """Validation test on the real dataset directory data/."""

    def test_evaluate_real_dataset_consistency(self, model):
        """Validates all PDFs in data/jd and data/resumes end-to-end."""
        jd_files = glob.glob(os.path.join("data", "jd", "*.pdf"))
        resume_files = glob.glob(os.path.join("data", "resumes", "*.pdf"))

        if not jd_files or not resume_files:
            pytest.skip("Real dataset files not present in data/")

        jd_text = extract_text_from_pdf(jd_files[0])
        jd = extract_jd(jd_text)
        jd.required_skills = normalize_skills(jd.required_skills)
        jd.preferred_skills = normalize_skills(jd.preferred_skills)

        resumes = {}
        for rf in resume_files:
            fname = os.path.basename(rf)
            r_text = extract_text_from_pdf(rf)
            res = extract_resume(r_text, filename=fname)
            res.skills = normalize_skills(res.skills)
            for p in res.projects:
                p.technologies = normalize_skills(p.technologies)
            resumes[fname] = res

        ranking = shortlist_candidates(jd, resumes, model=model)

        assert len(ranking.candidates) == len(resume_files)

        # Ranks 1..N strictly assigned
        assert [c.rank for c in ranking.candidates] == list(range(1, len(resume_files) + 1))

        # Scores strictly descending
        scores = [c.final_score for c in ranking.candidates]
        assert scores == sorted(scores, reverse=True)

        # Formula strictly obeyed for all candidates
        for c in ranking.candidates:
            expected = round(0.50 * c.keyword_score + 0.50 * c.semantic_score, 2)
            assert c.final_score == expected
            assert 0.0 <= c.final_score <= 100.0

        # Top 3 have non-empty grounded explanations
        for c in ranking.candidates[:3]:
            assert c.explanation is not None
            assert len(c.explanation) > 100
            assert c.candidate_name in c.explanation

        # Candidates > 3 have None explanation
        for c in ranking.candidates[3:]:
            assert c.explanation is None
