"""Keyword-based skill matching engine.

Matches candidate skills against JD requirements using normalized aliases and fuzzy matching.
To be implemented in Phase 3.
"""

from __future__ import annotations

from app.models.jd_models import JobDescription
from app.models.resume_models import Resume


def compute_keyword_score(jd: JobDescription, resume: Resume) -> dict:
    """Compute keyword matching score for a candidate against a JD.

    Args:
        jd: Structured job description.
        resume: Structured resume.

    Returns:
        Dict with keyword_score, matched/missing skills.
    """
    raise NotImplementedError("Keyword matching will be implemented in Phase 3.")
