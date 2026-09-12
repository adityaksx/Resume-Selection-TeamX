"""Shortlisting pipeline orchestration (plan.md §3, §14).

Coordinates JD and Resume matching, computes keyword and semantic scores,
calculates final scores, and ranks all candidates.
Keeps business logic decoupled from UI presentation.
"""

from __future__ import annotations

import logging
from typing import Mapping, Sequence

from sentence_transformers import SentenceTransformer

from app.explanation.explanation_generator import attach_top_explanations
from app.matching.keyword_matcher import compute_keyword_score
from app.matching.scorer import compute_final_score, rank_candidates
from app.matching.semantic_matcher import compute_semantic_details, get_embedding_model
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult
from app.models.resume_models import Resume

logger = logging.getLogger(__name__)


def score_candidate(
    jd: JobDescription,
    resume: Resume,
    filename: str | None = None,
    model: SentenceTransformer | None = None,
) -> CandidateResult:
    """Score a single candidate against a Job Description across keyword and semantic engines.

    Args:
        jd: Structured JobDescription instance.
        resume: Structured Resume instance.
        filename: Optional filename of the candidate resume.
        model: Optional pre-loaded SentenceTransformer model.

    Returns:
        Populated CandidateResult model with keyword, semantic, and final scores.
    """
    # 1. Phase 3 keyword matching
    keyword_result = compute_keyword_score(jd, resume)

    # 2. Phase 4 semantic matching
    semantic_result = compute_semantic_details(jd, resume, model=model)

    # 3. Phase 5 final score calculation
    final_score = compute_final_score(
        keyword_score=keyword_result["keyword_score"],
        semantic_score=semantic_result["semantic_score"],
    )

    return CandidateResult(
        candidate_name=resume.candidate_name,
        filename=filename,
        keyword_score=keyword_result["keyword_score"],
        semantic_score=semantic_result["semantic_score"],
        final_score=final_score,
        matched_required_skills=keyword_result["matched_required_skills"],
        missing_required_skills=keyword_result["missing_required_skills"],
        matched_preferred_skills=keyword_result["matched_preferred_skills"],
        missing_preferred_skills=keyword_result["missing_preferred_skills"],
        semantic_evidence=semantic_result["requirement_matches"],
    )


def shortlist_candidates(
    jd: JobDescription,
    resumes: Mapping[str, Resume] | Sequence[Resume],
    model: SentenceTransformer | None = None,
) -> RankingResult:
    """Orchestrate end-to-end shortlisting and ranking for all candidate resumes.

    Args:
        jd: Structured JobDescription instance.
        resumes: Mapping of filename -> Resume, or sequence of Resume objects.
        model: Optional pre-loaded SentenceTransformer model (cached if None).

    Returns:
        RankingResult with all candidates ordered best-to-worst.
    """
    if model is None:
        model = get_embedding_model()

    scored_candidates: list[CandidateResult] = []

    if isinstance(resumes, Mapping):
        for filename, resume in resumes.items():
            cand_res = score_candidate(jd, resume, filename=filename, model=model)
            scored_candidates.append(cand_res)
    else:
        for resume in resumes:
            cand_res = score_candidate(jd, resume, filename=None, model=model)
            scored_candidates.append(cand_res)

    ranking = rank_candidates(scored_candidates, jd_role_title=jd.role_title)
    ranking = attach_top_explanations(ranking, top_k=3)
    logger.info(
        "Shortlisted and ranked %d candidates. Top candidate: '%s' (score=%.2f)",
        len(ranking.candidates),
        ranking.candidates[0].candidate_name if ranking.candidates else "None",
        ranking.candidates[0].final_score if ranking.candidates else 0.0,
    )
    return ranking
