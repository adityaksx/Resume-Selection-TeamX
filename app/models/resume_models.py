"""Pydantic models for Resume data (plan.md §6)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Contact(BaseModel):
    """Candidate contact information."""

    email: str | None = Field(default=None)
    phone: str | None = Field(default=None)


class Experience(BaseModel):
    """A single work-experience entry."""

    role: str | None = Field(default=None)
    company: str | None = Field(default=None)
    duration: str | None = Field(default=None)
    description: str | None = Field(default=None)


class Project(BaseModel):
    """A single project entry."""

    name: str | None = Field(default=None)
    technologies: list[str] = Field(default_factory=list)
    description: str | None = Field(default=None)


class Education(BaseModel):
    """A single education entry."""

    degree: str | None = Field(default=None)
    institution: str | None = Field(default=None)
    duration: str | None = Field(default=None)


class Resume(BaseModel):
    """Structured representation of a candidate resume.

    If information is absent from the resume, fields stay at their defaults.
    Do NOT invent information.
    """

    candidate_name: str = Field(
        default="Unknown Candidate", description="Full name of the candidate"
    )
    contact: Contact = Field(default_factory=Contact)
    skills: list[str] = Field(default_factory=list)
    experience: list[Experience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)
    raw_text: str = Field(
        default="", description="Original extracted text (for semantic matching)"
    )
