"""Deterministic candidate comparison calculation (plan.md Phase 7D).

Computes numerical score deltas, skill intersections, and asymmetric gaps
between any two ranked candidates without generative LLMs.
"""

from __future__ import annotations

import logging

from app.models.comparison_models import CandidateComparison
from app.models.result_models import CandidateResult

logger = logging.getLogger(__name__)


def compare_candidates(cand_a: CandidateResult, cand_b: CandidateResult) -> CandidateComparison:
    """Perform deterministic side-by-side comparison between two candidates.

    Args:
        cand_a: First candidate.
        cand_b: Second candidate.

    Returns:
        Populated CandidateComparison model.
    """
    # Identify which candidate is ranked higher (lower rank number = better)
    rank_a = cand_a.rank if cand_a.rank is not None else 9999
    rank_b = cand_b.rank if cand_b.rank is not None else 9999

    if rank_a < rank_b:
        higher = cand_a.candidate_name
    elif rank_b < rank_a:
        higher = cand_b.candidate_name
    else:
        # If ranks are tied, use final score
        higher = cand_a.candidate_name if cand_a.final_score >= cand_b.final_score else cand_b.candidate_name

    final_diff = round(cand_a.final_score - cand_b.final_score, 2)
    kw_diff = round(cand_a.keyword_score - cand_b.keyword_score, 2)
    sem_diff = round(cand_a.semantic_score - cand_b.semantic_score, 2)
    rank_diff = abs(rank_a - rank_b)

    # Required skills comparison
    set_req_a = set(cand_a.matched_required_skills)
    set_req_b = set(cand_b.matched_required_skills)
    shared_req = sorted(list(set_req_a.intersection(set_req_b)))
    unique_req_a = sorted(list(set_req_a - set_req_b))
    unique_req_b = sorted(list(set_req_b - set_req_a))

    # Missing required skills comparison
    set_miss_a = set(cand_a.missing_required_skills)
    set_miss_b = set(cand_b.missing_required_skills)
    shared_miss = sorted(list(set_miss_a.intersection(set_miss_b)))
    unique_miss_a = sorted(list(set_miss_a - set_miss_b))
    unique_miss_b = sorted(list(set_miss_b - set_miss_a))

    # Preferred skills comparison
    set_pref_a = set(cand_a.matched_preferred_skills)
    set_pref_b = set(cand_b.matched_preferred_skills)
    shared_pref = sorted(list(set_pref_a.intersection(set_pref_b)))
    unique_pref_a = sorted(list(set_pref_a - set_pref_b))
    unique_pref_b = sorted(list(set_pref_b - set_pref_a))

    return CandidateComparison(
        candidate_a=cand_a,
        candidate_b=cand_b,
        higher_ranked_candidate=higher,
        rank_difference=rank_diff,
        final_score_difference=final_diff,
        keyword_score_difference=kw_diff,
        semantic_score_difference=sem_diff,
        shared_required_skills=shared_req,
        unique_required_a=unique_req_a,
        unique_required_b=unique_req_b,
        shared_missing_required=shared_miss,
        unique_missing_a=unique_miss_a,
        unique_missing_b=unique_miss_b,
        shared_preferred_skills=shared_pref,
        unique_preferred_a=unique_pref_a,
        unique_preferred_b=unique_pref_b,
    )
