"""Deterministic Resume extraction using regex, section parsing, and NLP skill extraction."""

from __future__ import annotations

import logging
from pathlib import Path
import re

from app.extraction.skill_extractor import extract_skills_from_text
from app.matching.skill_normalizer import normalize_skills
from app.models.resume_models import (
    Contact,
    Education,
    Experience,
    Project,
    Resume,
)

logger = logging.getLogger(__name__)

# Section heading regexes
_RESUME_HEADING_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "skills",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:technical\s+skills|skills|technologies|tech\s+stack|technical\s+expertise|core\s+competencies|tools\s*(?:&|and)\s*technologies|programming\s+languages)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "experience",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:work\s+experience|professional\s+experience|employment(?:\s+history)?|internships?|relevant\s+experience|experience)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "projects",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:projects|personal\s+projects|academic\s+projects|key\s+projects|technical\s+projects)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "education",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:education|academic\s+background|academic\s+qualifications|academics)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "certifications",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:certifications?|certificates?|licenses(?:\s*(?:&|and)\s*certifications)?)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "other",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:achievements|awards|interests|hobbies|extracurricular(?:s|\s+activities)?|languages|references|summary|professional\s+summary|profile|about\s+me)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
]

_DATE_PATTERN = re.compile(
    r"\b(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{4})\s*(?:[-–—to\s]+)\s*(?:(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|\d{4}|Present|Current|Ongoing)\b",
    re.IGNORECASE,
)

_DEGREE_PATTERN = re.compile(
    r"(?:B\.?S(?:\.c)?\.?|M\.?S(?:\.c)?\.?|B\.?Tech\.?|M\.?Tech\.?|B\.?E\.?|M\.?E\.?|Bachelor(?:'s)?(?:\s+of\s+[A-Za-z]+)?|Master(?:'s)?(?:\s+of\s+[A-Za-z]+)?|Ph\.?D\.?|Associate(?:'s)?|High\s+School|Diploma)(?:\s+in\s+[A-Za-z\s]+)?",
    re.IGNORECASE,
)


def _clean_bullet(line: str) -> str:
    """Strip leading bullets, numbers, and whitespace."""
    return re.sub(r"^[\s*•\-–—\d\.\)\:\?·]+", "", line).strip()


def _extract_name(lines: list[str], filename: str | None = None) -> str:
    """Extract candidate name using header heuristics with filename fallback."""
    # 1. Check for explicit "Name: John Doe"
    for line in lines[:10]:
        match = re.search(r"^(?:name|candidate(?:\s+name)?)\s*[:\-]\s*([A-Za-z\s.'-]+)$", line, re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            if candidate and len(candidate.split()) <= 4:
                return candidate

    # 2. Check first 5 non-empty lines before any section heading
    disallowed_keywords = [
        "resume", "curriculum", "vitae", "cv", "portfolio", "email", "phone",
        "github", "linkedin", "http", "@", ".com", "developer", "engineer",
        "intern", "skills", "experience", "education", "page", "contact",
    ]
    for line in lines[:5]:
        cleaned = _clean_bullet(line).strip()
        if not cleaned:
            continue
        lower = cleaned.lower()
        if any(d in lower for d in disallowed_keywords):
            continue
        words = cleaned.split()
        # A name usually has 1 to 4 words, predominantly alphabetic
        if 1 <= len(words) <= 4 and all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
            return cleaned

    # 3. Fallback to filename stem if provided
    if filename:
        stem = Path(filename).stem
        # Clean common artifacts: e.g. "Alex_Rivera_Resume" -> "Alex Rivera"
        stem = re.sub(r"(?:[-_]?(?:resume|cv|profile|internloom))", "", stem, flags=re.IGNORECASE)
        stem = re.sub(r"[_\-]+", " ", stem).strip()
        words = stem.split()
        if 1 <= len(words) <= 4 and all(re.match(r"^[A-Za-z.'-]+$", w) for w in words):
            return " ".join(w.capitalize() for w in words)

    return "Unknown Candidate"


def _extract_contact(text: str) -> Contact:
    """Extract email and phone number using regex."""
    email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    email = email_match.group(0) if email_match else None

    # Phone matching: standard formats (US, international, Indian)
    phone_pattern = re.compile(
        r"(?:(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+?\d{1,3}[-.\s]?\d{10}|\b\d{10}\b)"
    )
    phone_match = phone_pattern.search(text)
    phone = phone_match.group(0).strip() if phone_match else None

    return Contact(email=email, phone=phone)


def _parse_experience(text: str) -> list[Experience]:
    """Parse work experience block into structured Experience models."""
    if not text.strip():
        return []

    lines = text.splitlines()
    entries: list[Experience] = []
    current_role: str | None = None
    current_company: str | None = None
    current_duration: str | None = None
    current_desc: list[str] = []

    def save_current():
        nonlocal current_role, current_company, current_duration, current_desc
        if current_role or current_company or current_desc:
            desc_text = " ".join(current_desc).strip() if current_desc else None
            entries.append(
                Experience(
                    role=current_role,
                    company=current_company,
                    duration=current_duration,
                    description=desc_text,
                )
            )
        current_role, current_company, current_duration, current_desc = None, None, None, []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        date_match = _DATE_PATTERN.search(stripped)
        # Entry header if line contains a date or strong separator
        if date_match and len(stripped.split()) <= 15:
            save_current()
            current_duration = date_match.group(0).strip()
            # Remainder of the line often contains company and/or role
            remaining = stripped[:date_match.start()] + stripped[date_match.end():]
            remaining = remaining.strip(" -–—,|•")
            if " at " in remaining.lower():
                parts = re.split(r"\s+at\s+", remaining, flags=re.IGNORECASE)
                current_role, current_company = parts[0].strip(), parts[1].strip()
            elif any(sep in remaining for sep in ["|", ",", "–", "-"]):
                parts = re.split(r"[|,–\-]+", remaining)
                if len(parts) >= 2:
                    current_role = parts[0].strip()
                    current_company = parts[1].strip()
                else:
                    current_role = remaining
            else:
                current_role = remaining or None
        elif any(sep in stripped for sep in ["|", "–", "-"]) and not stripped.startswith(("•", "-", "*")) and len(stripped.split()) <= 10:
            # Possible header line without date: e.g. "Software Engineer | Acme Corp"
            parts = re.split(r"[|–\-]+", stripped)
            if len(parts) >= 2 and any(kw in parts[0].lower() for kw in ["developer", "engineer", "intern", "lead", "analyst"]):
                save_current()
                current_role = parts[0].strip()
                current_company = parts[1].strip()
            else:
                current_desc.append(_clean_bullet(stripped))
        else:
            current_desc.append(_clean_bullet(stripped))

    save_current()
    return entries


def _parse_projects(text: str) -> list[Project]:
    """Parse projects block into structured Project models."""
    if not text.strip():
        return []

    lines = text.splitlines()
    projects: list[Project] = []
    current_name: str | None = None
    current_techs: list[str] = []
    current_desc: list[str] = []

    def save_project():
        nonlocal current_name, current_techs, current_desc
        if current_name or current_desc:
            desc_text = " ".join(current_desc).strip() if current_desc else None
            # Extract technologies from description as well
            if desc_text:
                found = extract_skills_from_text(desc_text)
                current_techs.extend(found)
            projects.append(
                Project(
                    name=current_name or "Project",
                    technologies=normalize_skills(current_techs),
                    description=desc_text,
                )
            )
        current_name, current_techs, current_desc = None, [], []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Check for explicit tech stack line e.g. "Technologies: React, Node.js"
        tech_match = re.search(r"(?:technologies|tech\s+stack|tools\s+used)\s*[:\-]\s*(.+)$", stripped, re.IGNORECASE)
        if tech_match:
            current_techs.extend(extract_skills_from_text(tech_match.group(1)))
            continue

        # Detect project title line (e.g. "Project Name | React, Node.js" or "• E-commerce App - Description")
        clean = _clean_bullet(stripped)
        if "|" in clean and len(clean.split()) <= 12:
            save_project()
            parts = clean.split("|")
            current_name = parts[0].strip()
            current_techs.extend(extract_skills_from_text(parts[1]))
        elif re.match(r"^[A-Z][A-Za-z0-9\s'-]{2,40}(?:\s*[:\-]|\s*\(.*?\))?$", clean) and len(clean.split()) <= 6:
            save_project()
            current_name = clean
        else:
            current_desc.append(clean)

    save_project()
    return projects


def _parse_education(text: str) -> list[Education]:
    """Parse education block into structured Education models."""
    if not text.strip():
        return []

    lines = text.splitlines()
    education: list[Education] = []

    for line in lines:
        cleaned = _clean_bullet(line).strip()
        if not cleaned:
            continue

        degree_match = _DEGREE_PATTERN.search(cleaned)
        date_match = _DATE_PATTERN.search(cleaned)

        duration = date_match.group(0).strip() if date_match else None
        degree = degree_match.group(0).strip() if degree_match else None

        # Institution detection heuristics
        institution = None
        for inst_kw in ["University", "College", "Institute", "School", "Academy", "IIT", "NIT", "BITS"]:
            if inst_kw.lower() in cleaned.lower():
                # Extract institution segment
                parts = re.split(r"[,|–\-]+", cleaned)
                for part in parts:
                    if inst_kw.lower() in part.lower():
                        institution = part.strip()
                        break
                if not institution:
                    institution = cleaned
                break

        if degree or institution or duration:
            education.append(
                Education(
                    degree=degree,
                    institution=institution,
                    duration=duration,
                )
            )

    return education


def _parse_certifications(text: str) -> list[str]:
    """Extract list of certification titles from text."""
    if not text.strip():
        return []

    certs: list[str] = []
    for line in text.splitlines():
        cleaned = _clean_bullet(line).strip()
        if cleaned and len(cleaned) <= 120:
            certs.append(cleaned)
    return certs


def extract_resume(raw_text: str, filename: str | None = None) -> Resume:
    """Extract structured Resume from raw text deterministically.

    Args:
        raw_text: Cleaned text from a resume PDF.
        filename: Optional filename for candidate name fallback.

    Returns:
        A validated Resume model with raw_text preserved.

    Raises:
        ValueError: If raw_text is empty or blank.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot extract resume from empty text.")

    lines = raw_text.splitlines()

    # Section segmentation
    sections: dict[str, list[str]] = {
        "header": [],
        "skills": [],
        "experience": [],
        "projects": [],
        "education": [],
        "certifications": [],
        "other": [],
    }

    current_section = "header"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for sec_name, pattern in _RESUME_HEADING_PATTERNS:
            if pattern.match(stripped):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    # 1. Candidate Name
    candidate_name = _extract_name(sections["header"] or lines, filename=filename)

    # 2. Contact info (searched across entire raw text for robustness)
    contact = _extract_contact(raw_text)

    # 3. Skills extraction
    skills_text = "\n".join(sections["skills"])
    # Extract from skills section
    skills = extract_skills_from_text(skills_text)
    # Also extract skills mentioned across projects and experience
    exp_and_proj_text = "\n".join(sections["experience"] + sections["projects"])
    body_skills = extract_skills_from_text(exp_and_proj_text)
    all_skills = normalize_skills(skills + body_skills)

    # 4. Experience parsing
    experience_text = "\n".join(sections["experience"])
    experience = _parse_experience(experience_text)

    # 5. Projects parsing
    projects_text = "\n".join(sections["projects"])
    projects = _parse_projects(projects_text)

    # 6. Education parsing
    education_text = "\n".join(sections["education"])
    education = _parse_education(education_text)

    # 7. Certifications parsing
    certs_text = "\n".join(sections["certifications"])
    certifications = _parse_certifications(certs_text)

    logger.info(
        "Extracted Resume: candidate='%s', email='%s', skills=%d, exp=%d, proj=%d, edu=%d, certs=%d",
        candidate_name, contact.email, len(all_skills), len(experience),
        len(projects), len(education), len(certifications),
    )

    return Resume(
        candidate_name=candidate_name,
        contact=contact,
        skills=all_skills,
        experience=experience,
        projects=projects,
        education=education,
        certifications=certifications,
        raw_text=raw_text,
    )
