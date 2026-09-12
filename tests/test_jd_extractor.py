"""Tests for deterministic Job Description extraction."""

from __future__ import annotations

import pytest

from app.extraction.jd_extractor import extract_jd
from app.models.jd_models import JobDescription


SAMPLE_STANDARD_JD = """\
Job Title: Full Stack Developer Intern
Company: Acme Innovations

About Us:
Acme Innovations builds next-generation SaaS platforms.

Responsibilities:
• Develop scalable backend services using Node.js and Express.
• Build responsive user interfaces with React.
• Design and maintain MongoDB databases.
• Write clean, well-tested code with CI/CD integration.

Required Skills:
• React.js
• Node.js
• MongoDB
• REST API development
• Git

Preferred Skills:
• Docker
• TypeScript
• AWS

Qualifications:
• Currently pursuing a B.S. or B.Tech in Computer Science or related field.
• Strong problem-solving and analytical skills.
"""

SAMPLE_ALTERNATE_HEADINGS_JD = """\
Role: Junior Software Engineer
Organization: CloudTech Systems

What You'll Do:
1. Implement RESTful APIs with Python and FastAPI.
2. Collaborate with cross-functional product teams.

Must Have:
- Python
- PostgreSQL
- Docker

Nice to Have:
- Kubernetes
- GraphQL
"""

SAMPLE_MINIMAL_JD = """\
Backend Developer

Requirements:
- Python
- Django
- SQL
"""


class TestJDExtractor:
    """Tests for extract_jd()."""

    def test_extract_standard_jd(self):
        """Standard JD extracts all fields correctly."""
        jd = extract_jd(SAMPLE_STANDARD_JD)

        assert isinstance(jd, JobDescription)
        assert jd.role_title == "Full Stack Developer Intern"
        assert jd.company == "Acme Innovations"

        # Check required skills (normalized)
        assert "React" in jd.required_skills
        assert "Node.js" in jd.required_skills
        assert "MongoDB" in jd.required_skills
        assert "REST API" in jd.required_skills
        assert "Git" in jd.required_skills

        # Check preferred skills
        assert "Docker" in jd.preferred_skills
        assert "TypeScript" in jd.preferred_skills
        assert "AWS" in jd.preferred_skills

        # Check responsibilities and qualifications
        assert len(jd.responsibilities) >= 3
        assert len(jd.qualifications) >= 1
        assert "B.Tech" in jd.qualifications[0] or "Computer Science" in jd.qualifications[0]

        # Verify raw text preservation
        assert jd.raw_text == SAMPLE_STANDARD_JD

    def test_extract_alternate_headings(self):
        """JDs with alternate headings ('Must Have', 'Nice to Have', 'What You'll Do') work."""
        jd = extract_jd(SAMPLE_ALTERNATE_HEADINGS_JD)

        assert jd.role_title == "Junior Software Engineer"
        assert jd.company == "CloudTech Systems"

        assert "Python" in jd.required_skills
        assert "PostgreSQL" in jd.required_skills
        assert "Docker" in jd.required_skills

        assert "Kubernetes" in jd.preferred_skills
        assert "GraphQL" in jd.preferred_skills

        assert len(jd.responsibilities) >= 1

    def test_extract_minimal_jd(self):
        """Minimal JD without preferred skills or explicit company succeeds."""
        jd = extract_jd(SAMPLE_MINIMAL_JD)

        assert jd.role_title == "Backend Developer"
        assert "Python" in jd.required_skills
        assert "Django" in jd.required_skills
        assert "SQL" in jd.required_skills
        assert jd.preferred_skills == []

    def test_empty_text_raises_value_error(self):
        """Empty or whitespace-only text raises ValueError."""
        with pytest.raises(ValueError, match="empty text"):
            extract_jd("")

        with pytest.raises(ValueError, match="empty text"):
            extract_jd("   \n\t  ")

    def test_skill_deduplication(self):
        """Duplicate skill variants in JD are normalized and deduplicated."""
        text = """\
        Role: Frontend Engineer
        Requirements:
        - React
        - React.js
        - ReactJS
        - JavaScript
        - JS
        """
        jd = extract_jd(text)
        assert jd.required_skills.count("React") == 1
        assert jd.required_skills.count("JavaScript") == 1
