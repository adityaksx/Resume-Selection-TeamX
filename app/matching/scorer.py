"""Final score calculation and candidate ranking (plan.md §13, §14).

Combines keyword and semantic scores into a single final score and deterministically
ranks all candidates.
"""

from __future__ import annotations

import logging

from app.models.result_models import CandidateResult, RankingResult
from app.utils.config import get_settings

logger = logging.getLogger(__name__)


def compute_final_score(keyword_score: float, semantic_score: float) -> float:
    """Compute the weighted final score from keyword and semantic components.

    Formula:
        Final Score = (keyword_weight * keyword_score) + (semantic_weight * semantic_score)

    Args:
        keyword_score: Keyword matching score (0-100).
        semantic_score: Semantic similarity score (0-100).

    Returns:
        Final weighted score bounded between 0.0 and 100.0, rounded to 2 decimal places.
    """
    settings = get_settings()
    kw_weight = settings.keyword_weight    # default: 0.50
    sem_weight = settings.semantic_weight  # default: 0.50

    # Validate and bound component inputs to [0.0, 100.0]
    bounded_kw = max(0.0, min(100.0, float(keyword_score)))
    bounded_sem = max(0.0, min(100.0, float(semantic_score)))

    final_score = (kw_weight * bounded_kw) + (sem_weight * bounded_sem)
    bounded_final = round(max(0.0, min(100.0, final_score)), 2)

    logger.debug(
        "compute_final_score: kw=%.2f (w=%.2f), sem=%.2f (w=%.2f) -> final=%.2f",
        bounded_kw, kw_weight, bounded_sem, sem_weight, bounded_final,
    )
    return bounded_final


def rank_candidates(
    candidates: list[CandidateResult],
    jd_role_title: str | None = None,
) -> RankingResult:
    """Sort candidates deterministically by fit and assign rank positions.

    Deterministic tie-breaking order (plan.md §14):
        1. final_score descending (best fit first)
        2. keyword_score descending (higher keyword match breaks ties)
        3. number of matched required skills descending
        4. candidate_name ascending (alphabetical order as deterministic final tie-breaker)

    Args:
        candidates: List of CandidateResult objects to rank.
        jd_role_title: Optional title of the job description.

    Returns:
        RankingResult containing all candidates ordered from best to worst,
        with candidate.rank assigned (1-indexed).
    """
    if not candidates:
        return RankingResult(jd_role_title=jd_role_title, candidates=[])

    sorted_candidates = sorted(
        candidates,
        key=lambda c: (
            -c.final_score,
            -c.keyword_score,
            -len(c.matched_required_skills),
            c.candidate_name.lower(),
        ),
    )

    # Assign 1-indexed rank to each candidate
    ranked_list: list[CandidateResult] = []
    for rank_idx, cand in enumerate(sorted_candidates, start=1):
        cand_copy = cand.model_copy(update={"rank": rank_idx})
        ranked_list.append(cand_copy)

    logger.info("Ranked %d candidates for role '%s'.", len(ranked_list), jd_role_title)
    return RankingResult(jd_role_title=jd_role_title, candidates=ranked_list)
