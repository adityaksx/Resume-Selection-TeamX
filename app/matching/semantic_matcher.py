"""Semantic embedding-based matching engine (plan.md §10).

Uses local sentence-transformers (all-MiniLM-L6-v2) and cosine similarity
to match JD requirements against candidate resume evidence chunks.
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import numpy as np
from sentence_transformers import SentenceTransformer

from app.models.jd_models import JobDescription
from app.models.resume_models import Resume
from app.utils.config import get_settings

logger = logging.getLogger(__name__)

# Module-level model singleton and thread lock
_MODEL_LOCK = threading.Lock()
_CACHED_MODEL: SentenceTransformer | None = None
_CACHED_MODEL_NAME: str | None = None


def get_embedding_model(model_name: str | None = None) -> SentenceTransformer:
    """Load and return the local SentenceTransformer embedding model singleton.

    Loads the model once per process and caches it in memory.
    Attempts local cache first to ensure offline reliability.

    Args:
        model_name: Model identifier (defaults to settings.embedding_model).

    Returns:
        SentenceTransformer model instance.

    Raises:
        RuntimeError: If the model cannot be loaded.
    """
    global _CACHED_MODEL, _CACHED_MODEL_NAME

    if model_name is None:
        model_name = get_settings().embedding_model

    if _CACHED_MODEL is not None and _CACHED_MODEL_NAME == model_name:
        return _CACHED_MODEL

    with _MODEL_LOCK:
        if _CACHED_MODEL is not None and _CACHED_MODEL_NAME == model_name:
            return _CACHED_MODEL

        logger.info("Initializing SentenceTransformer model: %s", model_name)
        try:
            # First try loading strictly from local files (fast & offline)
            model = SentenceTransformer(model_name, local_files_only=True)
        except Exception as local_err:
            logger.debug("Local-only load failed (%s), attempting standard load...", local_err)
            try:
                model = SentenceTransformer(model_name)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to load embedding model '{model_name}': {exc}"
                ) from exc

        _CACHED_MODEL = model
        _CACHED_MODEL_NAME = model_name
        logger.info("SentenceTransformer model '%s' loaded successfully.", model_name)
        return _CACHED_MODEL


def build_jd_requirements(jd: JobDescription) -> list[str]:
    """Construct meaningful semantic requirement units from structured JD.

    Combines:
    - Required skills (phrased as capability requirements)
    - Key responsibilities (action-oriented sentences)
    - Qualifications (educational/technical background)
    - Preferred skills (as secondary capability context)

    Args:
        jd: Structured JobDescription instance.

    Returns:
        List of distinct requirement strings.
    """
    requirements: list[str] = []
    seen: set[str] = set()

    def add_req(text: str):
        cleaned = text.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            requirements.append(cleaned)

    # 1. Responsibilities (rich natural language context)
    for resp in jd.responsibilities:
        add_req(resp)

    # 2. Required skills
    for skill in jd.required_skills:
        add_req(f"Experience with {skill}")

    # 3. Qualifications
    for qual in jd.qualifications:
        add_req(qual)

    # 4. Preferred skills
    for pref in jd.preferred_skills:
        if pref not in jd.required_skills:
            add_req(f"Familiarity with {pref}")

    # Fallback to non-empty raw_text lines if no structured requirements exist
    if not requirements and jd.raw_text:
        for line in jd.raw_text.splitlines():
            cleaned = line.strip(" •*-–—\t")
            if len(cleaned.split()) >= 3 and len(cleaned) <= 150:
                add_req(cleaned)

    return requirements


def build_resume_evidence(resume: Resume) -> list[str]:
    """Construct meaningful semantic evidence chunks from structured Resume.

    Combines:
    - Projects (name + technologies + description)
    - Experience entries (role + company + description)
    - Skills summary
    - Education and certifications

    Args:
        resume: Structured Resume instance.

    Returns:
        List of distinct evidence text chunks.
    """
    evidence: list[str] = []
    seen: set[str] = set()

    def add_chunk(text: str):
        cleaned = text.strip()
        if cleaned and cleaned.lower() not in seen:
            seen.add(cleaned.lower())
            evidence.append(cleaned)

    # 1. Projects (highest evidence value for technical capabilities)
    for proj in resume.projects:
        parts: list[str] = []
        if proj.name:
            parts.append(f"Project: {proj.name}.")
        if proj.technologies:
            parts.append(f"Technologies: {', '.join(proj.technologies)}.")
        if proj.description:
            parts.append(proj.description)
        if parts:
            add_chunk(" ".join(parts))

    # 2. Experience entries
    for exp in resume.experience:
        parts = []
        header_parts = [p for p in [exp.role, exp.company, exp.duration] if p]
        if header_parts:
            parts.append(f"Experience: {' at '.join(header_parts[:2])}.")
        if exp.description:
            parts.append(exp.description)
        if parts:
            add_chunk(" ".join(parts))

    # 3. Skills summary chunk
    if resume.skills:
        add_chunk(f"Technical Skills: {', '.join(resume.skills)}.")

    # 4. Education
    for edu in resume.education:
        parts = [p for p in [edu.degree, edu.institution, edu.duration] if p]
        if parts:
            add_chunk(f"Education: {' from '.join(parts[:2])}.")

    # 5. Certifications
    if resume.certifications:
        add_chunk(f"Certifications: {', '.join(resume.certifications)}.")

    # Fallback to non-empty raw_text lines if no structured chunks exist
    if not evidence and resume.raw_text:
        for line in resume.raw_text.splitlines():
            cleaned = line.strip(" •*-–—\t")
            if len(cleaned.split()) >= 3 and len(cleaned) <= 200:
                add_chunk(cleaned)

    return evidence


def compute_requirement_similarities(
    jd: JobDescription,
    resume: Resume,
    model: SentenceTransformer | None = None,
) -> list[dict[str, Any]]:
    """Match each JD requirement against candidate evidence using cosine similarity.

    Encodes requirements and evidence in single batch operations, calculates the
    pairwise cosine similarity matrix, and identifies the best matching evidence
    chunk for each individual requirement.

    Args:
        jd: Structured JobDescription instance.
        resume: Structured Resume instance.
        model: Optional SentenceTransformer model (defaults to get_embedding_model()).

    Returns:
        List of dictionaries with requirement-level matches:
        [
            {
                "requirement": str,
                "best_matching_evidence": str,
                "similarity": float,        # 0.0 to 1.0
                "similarity_score": float,  # 0.0 to 100.0
            },
            ...
        ]
    """
    requirements = build_jd_requirements(jd)
    evidence = build_resume_evidence(resume)

    if not requirements:
        logger.debug("No JD requirements found for semantic matching.")
        return []

    if not evidence:
        logger.debug("No resume evidence chunks found for semantic matching.")
        return [
            {
                "requirement": req,
                "best_matching_evidence": "",
                "similarity": 0.0,
                "similarity_score": 0.0,
            }
            for req in requirements
        ]

    if model is None:
        model = get_embedding_model()

    # Batch encode both sets with unit normalization
    req_embeddings = model.encode(
        requirements,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    ev_embeddings = model.encode(
        evidence,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )

    # Cosine similarity matrix via dot product: shape (len(requirements), len(evidence))
    sim_matrix = np.dot(req_embeddings, ev_embeddings.T)

    results: list[dict[str, Any]] = []
    for i, req in enumerate(requirements):
        best_idx = int(np.argmax(sim_matrix[i]))
        raw_sim = float(sim_matrix[i, best_idx])
        # Clamp to [0.0, 1.0]
        clamped_sim = max(0.0, min(1.0, raw_sim))

        results.append(
            {
                "requirement": req,
                "best_matching_evidence": evidence[best_idx],
                "similarity": round(clamped_sim, 4),
                "similarity_score": round(clamped_sim * 100.0, 2),
            }
        )

    return results


def compute_semantic_score(
    jd: JobDescription,
    resume: Resume,
    model: SentenceTransformer | None = None,
) -> float:
    """Compute the overall semantic similarity score (0-100) between a JD and a Resume.

    Calculates the average of the maximum similarity found for each JD requirement
    against candidate evidence.

    Args:
        jd: Structured JobDescription instance.
        resume: Structured Resume instance.
        model: Optional SentenceTransformer model (defaults to get_embedding_model()).

    Returns:
        Semantic similarity score bounded in [0.0, 100.0].
    """
    matches = compute_requirement_similarities(jd, resume, model=model)
    if not matches:
        return 0.0

    avg_similarity = sum(m["similarity"] for m in matches) / len(matches)
    score = round(max(0.0, min(100.0, avg_similarity * 100.0)), 2)
    return score


def compute_semantic_details(
    jd: JobDescription,
    resume: Resume,
    model: SentenceTransformer | None = None,
) -> dict[str, Any]:
    """Compute semantic score along with detailed requirement-level evidence matches.

    Args:
        jd: Structured JobDescription instance.
        resume: Structured Resume instance.
        model: Optional SentenceTransformer model (defaults to get_embedding_model()).

    Returns:
        Dict with 'semantic_score' and 'requirement_matches'.
    """
    matches = compute_requirement_similarities(jd, resume, model=model)
    if not matches:
        return {"semantic_score": 0.0, "requirement_matches": []}

    avg_similarity = sum(m["similarity"] for m in matches) / len(matches)
    score = round(max(0.0, min(100.0, avg_similarity * 100.0)), 2)

    return {
        "semantic_score": score,
        "requirement_matches": matches,
    }
