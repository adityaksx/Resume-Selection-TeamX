"""Data models for JD Fairness and Narrow-Language Analysis (plan.md Phase 7G)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FairnessFinding(BaseModel):
    """A specific phrase or requirement identified for human review."""

    phrase: str = Field(description="Exact phrase or requirement in JD")
    issue: str = Field(description="Category of issue, e.g. Subjective Phrasing, Narrow Requirement, Restrictive Qualification")
    rationale: str = Field(description="Why this wording may unnecessarily narrow candidate diversity")
    suggested_alternative: str = Field(description="Recommended replacement phrasing")
    human_review_warning: str = Field(
        default="Potential issue — human review recommended.",
        description="Standard advisory disclaimer",
    )


class JDFairnessReport(BaseModel):
    """Complete advisory report on JD language and inclusivity."""

    role_title: str = ""
    findings: list[FairnessFinding] = Field(default_factory=list)
    overall_summary: str = ""
    disclaimer: str = Field(
        default="Advisory analysis only. Potential issue — human review recommended. Does not constitute legal advice or alter candidate rankings.",
    )
