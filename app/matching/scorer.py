"""Final score calculation and candidate ranking.

Combines keyword and semantic scores into a single final score.
To be implemented in Phase 5.
"""

from __future__ import annotations

from app.models.result_models import CandidateResult, RankingResult


def compute_final_score(keyword_score: float, semantic_score: float) -> float:
    """Compute the weighted final score (plan.md §11).

    Args:
        keyword_score: Keyword matching score (0-100).
        semantic_score: Semantic similarity score (0-100).

    Returns:
        Final weighted score (0-100).
    """
    raise NotImplementedError("Scoring will be implemented in Phase 5.")


def rank_candidates(candidates: list[CandidateResult]) -> RankingResult:
    """Sort candidates by final_score descending.

    Args:
        candidates: List of scored CandidateResult objects.

    Returns:
        RankingResult with candidates ordered best-to-worst.
    """
    raise NotImplementedError("Ranking will be implemented in Phase 5.")
