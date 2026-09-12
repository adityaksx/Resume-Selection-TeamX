"""Semantic embedding-based matching engine.

Uses sentence-transformers and cosine similarity to match resumes to JDs.
To be implemented in Phase 4.
"""

from __future__ import annotations

from app.models.jd_models import JobDescription
from app.models.resume_models import Resume


def compute_semantic_score(jd: JobDescription, resume: Resume) -> float:
    """Compute semantic similarity score between a JD and a resume.

    Args:
        jd: Structured job description.
        resume: Structured resume.

    Returns:
        Semantic similarity score (0-100).
    """
    raise NotImplementedError("Semantic matching will be implemented in Phase 4.")
