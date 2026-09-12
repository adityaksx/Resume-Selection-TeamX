"""Top-3 explanation generation using Gemini API.

Generates natural-language explanations from pre-calculated evidence.
To be implemented in Phase 6.
"""

from __future__ import annotations

from app.models.result_models import CandidateResult


def generate_explanation(candidate: CandidateResult) -> str:
    """Generate a natural-language explanation for a top-3 candidate.

    Args:
        candidate: A CandidateResult with all scores and evidence filled.

    Returns:
        A human-readable explanation string.
    """
    raise NotImplementedError("Explanation generation will be implemented in Phase 6.")
