"""Tests for Phase 3: Keyword skill matching engine (plan.md §11)."""

from __future__ import annotations

import pytest

from app.matching.keyword_matcher import compute_keyword_score
from app.models.jd_models import JobDescription
from app.models.resume_models import Project, Resume


class TestKeywordMatching:
    """Test suite for compute_keyword_score()."""

    # -----------------------------------------------------------------------
    # Scenario A: Exact match
    # -----------------------------------------------------------------------
    def test_scenario_a_exact_match(self):
        """JD: React, Node.js, MongoDB | Resume: React, Node.js, MongoDB -> 100% required match."""
        jd = JobDescription(required_skills=["React", "Node.js", "MongoDB"])
        resume = Resume(skills=["React", "Node.js", "MongoDB"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 100.0
        assert result["preferred_match_score"] == 0.0
        assert result["keyword_score"] == 100.0
        assert set(result["matched_required_skills"]) == {"React", "Node.js", "MongoDB"}
        assert result["missing_required_skills"] == []

    # -----------------------------------------------------------------------
    # Scenario B: Partial match
    # -----------------------------------------------------------------------
    def test_scenario_b_partial_match(self):
        """JD: React, Node.js, MongoDB, Git | Resume: React, Node.js -> 2/4 (50%) match."""
        jd = JobDescription(required_skills=["React", "Node.js", "MongoDB", "Git"])
        resume = Resume(skills=["React", "Node.js"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 50.0
        assert result["keyword_score"] == 50.0
        assert set(result["matched_required_skills"]) == {"React", "Node.js"}
        assert set(result["missing_required_skills"]) == {"MongoDB", "Git"}

    # -----------------------------------------------------------------------
    # Scenario C: Alias match
    # -----------------------------------------------------------------------
    def test_scenario_c_alias_match(self):
        """JD: Node.js, MongoDB | Resume: NodeJS, Mongo DB -> both matched via aliases."""
        jd = JobDescription(required_skills=["Node.js", "MongoDB"])
        resume = Resume(skills=["NodeJS", "Mongo DB"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 100.0
        assert result["keyword_score"] == 100.0
        assert set(result["matched_required_skills"]) == {"Node.js", "MongoDB"}
        assert result["missing_required_skills"] == []

    # -----------------------------------------------------------------------
    # Scenario D: Preferred skills weighting
    # -----------------------------------------------------------------------
    def test_scenario_d_preferred_skills(self):
        """Required: React, Node.js (matched 2/2 = 100%).

        Preferred: Docker, TypeScript (matched 1/2 = 50%).
        Score = 0.85 * 100 + 0.15 * 50 = 85.0 + 7.5 = 92.5.
        """
        jd = JobDescription(
            required_skills=["React", "Node.js"],
            preferred_skills=["Docker", "TypeScript"],
        )
        resume = Resume(skills=["React", "NodeJS", "Docker"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 100.0
        assert result["preferred_match_score"] == 50.0
        assert result["keyword_score"] == 92.5
        assert set(result["matched_required_skills"]) == {"React", "Node.js"}
        assert result["missing_required_skills"] == []
        assert result["matched_preferred_skills"] == ["Docker"]
        assert result["missing_preferred_skills"] == ["TypeScript"]

    # -----------------------------------------------------------------------
    # Scenario E: No preferred skills
    # -----------------------------------------------------------------------
    def test_scenario_e_no_preferred_skills(self):
        """JD has no preferred skills: keyword score is 100% determined by required skills."""
        jd = JobDescription(required_skills=["React", "Node.js"])
        resume = Resume(skills=["React"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 50.0
        assert result["preferred_match_score"] == 0.0
        assert result["keyword_score"] == 50.0
        assert result["matched_required_skills"] == ["React"]
        assert result["missing_required_skills"] == ["Node.js"]

    # -----------------------------------------------------------------------
    # Scenario F: No required skills / empty skills handling
    # -----------------------------------------------------------------------
    def test_scenario_f_no_required_skills_with_preferred(self):
        """JD with only preferred skills: score based on preferred skills without division by zero."""
        jd = JobDescription(required_skills=[], preferred_skills=["Docker", "AWS"])
        resume = Resume(skills=["Docker"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["preferred_match_score"] == 50.0
        assert result["keyword_score"] == 50.0
        assert result["matched_required_skills"] == []
        assert result["missing_required_skills"] == []
        assert result["matched_preferred_skills"] == ["Docker"]
        assert result["missing_preferred_skills"] == ["AWS"]

    def test_scenario_f_empty_jd_and_empty_resume(self):
        """Completely empty skills on both sides handles cleanly."""
        jd = JobDescription(required_skills=[], preferred_skills=[])
        resume = Resume(skills=[])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["preferred_match_score"] == 0.0
        assert result["keyword_score"] == 0.0
        assert result["matched_required_skills"] == []
        assert result["missing_required_skills"] == []

    # -----------------------------------------------------------------------
    # Scenario G: False positive prevention
    # -----------------------------------------------------------------------
    def test_scenario_g_java_vs_javascript(self):
        """Java must NOT match JavaScript."""
        jd = JobDescription(required_skills=["Java"])
        resume = Resume(skills=["JavaScript"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["matched_required_skills"] == []
        assert result["missing_required_skills"] == ["Java"]

    def test_scenario_g_c_vs_cpp(self):
        """C must NOT match C++."""
        jd = JobDescription(required_skills=["C"])
        resume = Resume(skills=["C++"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["matched_required_skills"] == []
        assert result["missing_required_skills"] == ["C"]

    def test_scenario_g_git_vs_github(self):
        """Git must NOT match GitHub unless Git is explicitly present."""
        jd = JobDescription(required_skills=["Git"])
        resume = Resume(skills=["GitHub"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["matched_required_skills"] == []
        assert result["missing_required_skills"] == ["Git"]

    def test_scenario_g_aws_vs_azure(self):
        """AWS must NOT match Azure."""
        jd = JobDescription(required_skills=["AWS"])
        resume = Resume(skills=["Azure"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["missing_required_skills"] == ["AWS"]

    def test_scenario_g_react_vs_react_native(self):
        """React must NOT match React Native."""
        jd = JobDescription(required_skills=["React"])
        resume = Resume(skills=["React Native"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 0.0
        assert result["missing_required_skills"] == ["React"]

    # -----------------------------------------------------------------------
    # Scenario H: Duplicate aliases deduplication
    # -----------------------------------------------------------------------
    def test_scenario_h_duplicate_aliases(self):
        """Resume with multiple aliases of the same skill collapses to one canonical skill."""
        jd = JobDescription(required_skills=["React", "Node.js"])
        resume = Resume(skills=["React", "ReactJS", "React.js"])

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 50.0
        assert result["matched_required_skills"] == ["React"]
        assert result["missing_required_skills"] == ["Node.js"]

    # -----------------------------------------------------------------------
    # Scenario I: Skills from project technologies
    # -----------------------------------------------------------------------
    def test_scenario_i_skills_from_projects(self):
        """Skills mentioned in resume.projects[*].technologies contribute to matching."""
        jd = JobDescription(required_skills=["React", "Node.js", "Docker"])
        resume = Resume(
            skills=["React"],
            projects=[
                Project(name="API Server", technologies=["Node.js", "Docker"]),
            ],
        )

        result = compute_keyword_score(jd, resume)

        assert result["required_match_score"] == 100.0
        assert set(result["matched_required_skills"]) == {"React", "Node.js", "Docker"}
        assert result["missing_required_skills"] == []

    # -----------------------------------------------------------------------
    # Scenario J: Immutability test
    # -----------------------------------------------------------------------
    def test_scenario_j_does_not_mutate_inputs(self):
        """compute_keyword_score does NOT mutate the original JD and Resume models."""
        jd = JobDescription(required_skills=["reactjs", "node js"])
        resume = Resume(skills=["mongo db"])

        original_jd_req = list(jd.required_skills)
        original_res_skills = list(resume.skills)

        _ = compute_keyword_score(jd, resume)

        assert jd.required_skills == original_jd_req
        assert resume.skills == original_res_skills
