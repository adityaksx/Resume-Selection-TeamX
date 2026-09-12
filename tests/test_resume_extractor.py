"""Tests for deterministic Resume extraction."""

from __future__ import annotations

import pytest

from app.extraction.resume_extractor import extract_resume
from app.models.resume_models import Resume


SAMPLE_RESUME = """\
Alex Rivera
alex.rivera@example.com | (555) 234-5678 | San Francisco, CA
linkedin.com/in/alexrivera | github.com/alexrivera

Technical Skills:
• Languages: JavaScript, TypeScript, Python, HTML5, CSS3
• Frameworks & Libraries: ReactJS, Node.js, Express.js, Tailwind CSS
• Databases & Tools: MongoDB, PostgreSQL, Docker, Git, RESTful API

Work Experience:
Software Engineering Intern at Nexus Labs | Jun 2023 - Aug 2023
• Built scalable REST APIs using Node.js and Express.
• Integrated MongoDB database models and optimized queries.
• Collaborated in an agile team using Git for version control.

Projects:
E-Commerce Web Application | React, Node.js, MongoDB
• Developed a full-stack e-commerce store with user authentication.
• Implemented shopping cart and Stripe checkout integration.

Task Management Dashboard
• Created a responsive dashboard using React and Tailwind CSS.
• Deployed application with Docker containerization.

Education:
B.S. in Computer Science, University of California, Berkeley | 2020 - 2024

Certifications:
• AWS Certified Cloud Practitioner
• Meta Front-End Developer Certificate
"""

SAMPLE_MINIMAL_RESUME = """\
Jane Doe
jane.doe@techmail.org

Skills:
Python, Django, SQL

Projects:
Weather Forecast App
Simple CLI weather app fetching data via weather API.
"""


class TestResumeExtractor:
    """Tests for extract_resume()."""

    def test_extract_standard_resume(self):
        """Standard resume extracts all components cleanly."""
        resume = extract_resume(SAMPLE_RESUME, filename="Alex_Rivera_Resume.pdf")

        assert isinstance(resume, Resume)
        assert resume.candidate_name == "Alex Rivera"

        # Contact info
        assert resume.contact.email == "alex.rivera@example.com"
        assert resume.contact.phone == "(555) 234-5678"

        # Skills (normalized)
        assert "JavaScript" in resume.skills
        assert "TypeScript" in resume.skills
        assert "Python" in resume.skills
        assert "React" in resume.skills
        assert "Node.js" in resume.skills
        assert "Express" in resume.skills
        assert "MongoDB" in resume.skills
        assert "PostgreSQL" in resume.skills
        assert "Docker" in resume.skills
        assert "Git" in resume.skills
        assert "REST API" in resume.skills

        # Experience
        assert len(resume.experience) >= 1
        exp = resume.experience[0]
        assert exp.duration is not None
        assert "2023" in exp.duration
        assert exp.company is not None and "Nexus Labs" in exp.company

        # Projects
        assert len(resume.projects) >= 2
        proj_names = [p.name for p in resume.projects]
        assert any("E-Commerce" in name for name in proj_names if name)

        # Education
        assert len(resume.education) >= 1
        edu = resume.education[0]
        assert edu.degree is not None and "B.S." in edu.degree

        # Certifications
        assert len(resume.certifications) >= 2
        assert any("AWS" in c for c in resume.certifications)

        # Raw text
        assert resume.raw_text == SAMPLE_RESUME

    def test_filename_fallback_name(self):
        """When header has no clear name, fallback to cleaned filename stem."""
        text = """\
        curriculum vitae
        john.smith@example.com
        (123) 456-7890
        
        Skills:
        Python, Go
        """
        resume = extract_resume(text, filename="John_Smith_Resume.pdf")
        assert resume.candidate_name == "John Smith"

    def test_minimal_resume(self):
        """Minimal resume without experience or education succeeds gracefully."""
        resume = extract_resume(SAMPLE_MINIMAL_RESUME)

        assert resume.candidate_name == "Jane Doe"
        assert resume.contact.email == "jane.doe@techmail.org"
        assert "Python" in resume.skills
        assert "Django" in resume.skills
        assert "SQL" in resume.skills
        assert resume.experience == []
        assert len(resume.projects) >= 1

    def test_empty_resume_raises_value_error(self):
        """Empty or whitespace text raises ValueError."""
        with pytest.raises(ValueError, match="empty text"):
            extract_resume("")

        with pytest.raises(ValueError, match="empty text"):
            extract_resume("   \n\t  ")

    def test_skills_from_experience_and_projects(self):
        """Skills mentioned in experience and projects are extracted into resume skills."""
        text = """\
        Sam Wilson
        sam@example.com
        
        Experience:
        Backend Engineer at Startup
        Built data pipelines with PyTorch and Redis.
        
        Projects:
        Search Engine
        Implemented inverted index using Rust and Docker.
        """
        resume = extract_resume(text)
        assert "PyTorch" in resume.skills
        assert "Redis" in resume.skills
        assert "Rust" in resume.skills
        assert "Docker" in resume.skills
