"""Pydantic models for Job Description data (plan.md §5)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobDescription(BaseModel):
    """Structured representation of a Job Description.

    Fields may be empty/null when the JD doesn't contain that info.
    """

    role_title: str | None = Field(
        default=None, description="Job title, e.g. 'Junior Full Stack Developer Intern'"
    )
    company: str | None = Field(
        default=None, description="Hiring company name"
    )
    required_skills: list[str] = Field(
        default_factory=list, description="Skills explicitly required"
    )
    preferred_skills: list[str] = Field(
        default_factory=list, description="Nice-to-have / preferred skills"
    )
    responsibilities: list[str] = Field(
        default_factory=list, description="Key responsibilities of the role"
    )
    qualifications: list[str] = Field(
        default_factory=list, description="Education or qualification requirements"
    )
    raw_text: str = Field(
        default="", description="Original extracted text (for semantic matching)"
    )
