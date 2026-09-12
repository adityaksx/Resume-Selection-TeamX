"""Smoke test for end-to-end PDF parse and deterministic extraction pipeline."""

from __future__ import annotations

import fitz  # PyMuPDF
import pytest

from app.parsers.pdf_parser import extract_text_from_pdf
from app.extraction.jd_extractor import extract_jd
from app.extraction.resume_extractor import extract_resume


SAMPLE_JD_TEXT = """\
Job Title: Full Stack Developer Intern
Company: Nexora Innovations

About Us:
Nexora Innovations is a fast-growing tech startup building modern developer tools.

Role Responsibilities:
• Build and maintain scalable REST APIs using Node.js and Express.
• Develop responsive and intuitive frontend interfaces with React.
• Design data models and queries with MongoDB.
• Collaborate with team members using Git and participate in code reviews.

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
• Currently pursuing a B.Tech or B.S. in Computer Science or related field.
• Strong foundation in data structures and algorithms.
"""

SAMPLE_RESUME_TEXT = """\
Rahul Sharma
rahul.sharma@example.com | (555) 432-8765 | Bangalore, India
github.com/rahulsharma | linkedin.com/in/rahulsharma

Technical Skills:
Languages: JavaScript, TypeScript, Python, HTML, CSS
Frameworks & Libraries: React, Node.js, Express.js
Databases & Cloud: MongoDB, PostgreSQL, Docker, AWS
Tools: Git, Postman, Linux

Experience:
Full Stack Intern at WebSphere Labs | Jan 2024 - Jul 2024
• Developed REST APIs using Node.js, Express, and MongoDB.
• Built responsive UI components with React and Tailwind CSS.
• Managed codebase versioning and feature branching with Git.

Projects:
DevPortal - Cloud Developer Platform | React, Node.js, Docker
• Built an end-to-end portal for deploying microservices.
• Integrated container management using Docker.

E-Commerce Storefront
• Built an interactive shopping platform using React and MongoDB.

Education:
B.Tech in Computer Science, National Institute of Technology | 2021 - 2025

Certifications:
• AWS Certified Cloud Practitioner
"""


def _create_pdf(text: str, filepath: str) -> None:
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(54, 54, 550, 750)
    page.insert_textbox(rect, text, fontsize=10)
    doc.save(filepath)
    doc.close()


def test_end_to_end_smoke(tmp_path):
    """Smoke test: PDF generation -> PyMuPDF parse -> Deterministic extraction."""
    jd_path = str(tmp_path / "Nexora_JD.pdf")
    resume_path = str(tmp_path / "Rahul_Sharma_Resume.pdf")

    _create_pdf(SAMPLE_JD_TEXT, jd_path)
    _create_pdf(SAMPLE_RESUME_TEXT, resume_path)

    # 1. PyMuPDF parsing
    jd_text = extract_text_from_pdf(jd_path)
    resume_text = extract_text_from_pdf(resume_path)

    assert len(jd_text) > 100
    assert len(resume_text) > 100

    # 2. Deterministic JD extraction
    jd = extract_jd(jd_text)
    assert jd.role_title == "Full Stack Developer Intern"
    assert jd.company == "Nexora Innovations"
    for s in ["React", "Node.js", "MongoDB", "REST API", "Git"]:
        assert s in jd.required_skills
    for s in ["Docker", "TypeScript", "AWS"]:
        assert s in jd.preferred_skills

    # 3. Deterministic Resume extraction
    resume = extract_resume(resume_text, filename="Rahul_Sharma_Resume.pdf")
    assert resume.candidate_name == "Rahul Sharma"
    assert resume.contact.email == "rahul.sharma@example.com"
    assert "(555) 432-8765" in resume.contact.phone
    for s in ["React", "Node.js", "MongoDB", "Express", "TypeScript", "Docker", "Git", "REST API"]:
        assert s in resume.skills
    assert len(resume.experience) >= 1
    assert len(resume.projects) >= 2
    assert len(resume.education) >= 1
    assert len(resume.certifications) >= 1
