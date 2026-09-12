"""Matching engine modules (keyword + semantic + scoring + orchestration)."""

from app.matching.keyword_matcher import compute_keyword_score
from app.matching.pipeline import score_candidate, shortlist_candidates
from app.matching.scorer import compute_final_score, rank_candidates
from app.matching.semantic_matcher import compute_semantic_details, compute_semantic_score
from app.matching.skill_normalizer import normalize_skill, normalize_skills

__all__ = [
    "compute_keyword_score",
    "compute_semantic_score",
    "compute_semantic_details",
    "compute_final_score",
    "rank_candidates",
    "score_candidate",
    "shortlist_candidates",
    "normalize_skill",
    "normalize_skills",
]
