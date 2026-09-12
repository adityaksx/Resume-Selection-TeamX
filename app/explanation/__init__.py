"""Explanation module for Phase 6: Top-3 Explainable Shortlist."""

from app.explanation.explanation_generator import (
    attach_top_explanations,
    generate_candidate_explanation,
)

__all__ = [
    "generate_candidate_explanation",
    "attach_top_explanations",
]
