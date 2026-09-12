"""Keyword-based skill matching engine (plan.md §11).

Matches candidate skills against JD requirements using normalized canonical
skills and exact set comparison.
"""

from __future__ import annotations

import logging
from typing import Any

from app.matching.skill_normalizer import normalize_skills
from app.models.jd_models import JobDescription
from app.models.resume_models import Resume
from app.utils.config import get_settings

logger = logging.getLogger(__name__)


def compute_keyword_score(jd: JobDescription, resume: Resume) -> dict[str, Any]:
    """Compute keyword matching score for a candidate against a Job Description.

    Strategy:
        1. Normalize and deduplicate JD required skills.
        2. Normalize and deduplicate JD preferred skills (excluding skills already in required).
        3. Collect, normalize, and deduplicate all candidate skills (from resume.skills
           and resume.projects[*].technologies).
        4. Match candidate skills against required and preferred skills using exact canonical match.
        5. Calculate required_match_score, preferred_match_score, and weighted keyword_score.

    Args:
        jd: Structured JobDescription instance (not mutated).
        resume: Structured Resume instance (not mutated).

    Returns:
        Dictionary with scores (0-100) and lists of matched/missing skills:
        {
            "keyword_score": float,
            "required_match_score": float,
            "preferred_match_score": float,
            "matched_required_skills": list[str],
            "missing_required_skills": list[str],
            "matched_preferred_skills": list[str],
            "missing_preferred_skills": list[str],
        }
    """
    settings = get_settings()
    req_weight = settings.required_skill_weight    # default: 0.85
    pref_weight = settings.preferred_skill_weight  # default: 0.15

    # 1. Normalize JD requirements
    norm_required = normalize_skills(jd.required_skills)
    norm_preferred_raw = normalize_skills(jd.preferred_skills)
    # Exclude preferred skills that are already listed as required
    norm_preferred = [s for s in norm_preferred_raw if s not in set(norm_required)]

    # 2. Extract and normalize candidate skills (resume skills + project technologies)
    candidate_skills_pool: list[str] = list(resume.skills)
    for proj in resume.projects:
        if proj.technologies:
            candidate_skills_pool.extend(proj.technologies)

    candidate_skills_norm = normalize_skills(candidate_skills_pool)
    candidate_skills_set = set(candidate_skills_norm)

    # 3. Match skills
    matched_required = [s for s in norm_required if s in candidate_skills_set]
    missing_required = [s for s in norm_required if s not in candidate_skills_set]

    matched_preferred = [s for s in norm_preferred if s in candidate_skills_set]
    missing_preferred = [s for s in norm_preferred if s not in candidate_skills_set]

    # 4. Calculate match ratios and scores
    total_required = len(norm_required)
    total_preferred = len(norm_preferred)

    if total_required > 0 and total_preferred > 0:
        required_match_ratio = len(matched_required) / total_required
        preferred_match_ratio = len(matched_preferred) / total_preferred

        required_match_score = required_match_ratio * 100.0
        preferred_match_score = preferred_match_ratio * 100.0
        keyword_score = (
            req_weight * required_match_score
            + pref_weight * preferred_match_score
        )
    elif total_required > 0 and total_preferred == 0:
        required_match_ratio = len(matched_required) / total_required
        required_match_score = required_match_ratio * 100.0
        preferred_match_score = 0.0
        keyword_score = required_match_score
    elif total_required == 0 and total_preferred > 0:
        preferred_match_ratio = len(matched_preferred) / total_preferred
        required_match_score = 0.0
        preferred_match_score = preferred_match_ratio * 100.0
        keyword_score = preferred_match_score
    else:  # total_required == 0 and total_preferred == 0
        required_match_score = 0.0
        preferred_match_score = 0.0
        keyword_score = 0.0

    # 5. Bound and round scores
    res_keyword = round(max(0.0, min(100.0, keyword_score)), 2)
    res_required = round(max(0.0, min(100.0, required_match_score)), 2)
    res_preferred = round(max(0.0, min(100.0, preferred_match_score)), 2)

    logger.debug(
        "Keyword match: req=%d/%d (%.1f), pref=%d/%d (%.1f), score=%.1f",
        len(matched_required), total_required, res_required,
        len(matched_preferred), total_preferred, res_preferred,
        res_keyword,
    )

    return {
        "keyword_score": res_keyword,
        "required_match_score": res_required,
        "preferred_match_score": res_preferred,
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
    }
