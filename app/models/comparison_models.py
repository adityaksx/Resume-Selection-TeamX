"""Data models for candidate comparison (plan.md Phase 7D)."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.result_models import CandidateResult


class CandidateComparison(BaseModel):
    """Structured deterministic comparison between two ranked candidates."""

    candidate_a: CandidateResult
    candidate_b: CandidateResult

    higher_ranked_candidate: str = Field(description="Name of the candidate with higher rank position")
    rank_difference: int = Field(description="Difference in rank (rank_b - rank_a if a higher)")

    final_score_difference: float = Field(description="candidate_a.final_score - candidate_b.final_score")
    keyword_score_difference: float = Field(description="candidate_a.keyword_score - candidate_b.keyword_score")
    semantic_score_difference: float = Field(description="candidate_a.semantic_score - candidate_b.semantic_score")

    # Required skills comparison
    shared_required_skills: list[str] = Field(default_factory=list)
    unique_required_a: list[str] = Field(default_factory=list, description="Skills matched by A but not B")
    unique_required_b: list[str] = Field(default_factory=list, description="Skills matched by B but not A")
    shared_missing_required: list[str] = Field(default_factory=list)
    unique_missing_a: list[str] = Field(default_factory=list, description="Skills missing in A but matched in B")
    unique_missing_b: list[str] = Field(default_factory=list, description="Skills missing in B but matched in A")

    # Preferred skills comparison
    shared_preferred_skills: list[str] = Field(default_factory=list)
    unique_preferred_a: list[str] = Field(default_factory=list)
    unique_preferred_b: list[str] = Field(default_factory=list)

    # Optional natural language explanation
    ai_explanation: str | None = Field(default=None, description="AI or deterministic explanation of comparison")
