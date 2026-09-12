"""Deterministic Job Description extraction using regex and rule-based section parsing."""

from __future__ import annotations

import logging
import re

from app.extraction.skill_extractor import extract_skills_from_text
from app.matching.skill_normalizer import normalize_skills
from app.models.jd_models import JobDescription

logger = logging.getLogger(__name__)

# Regex patterns for section headings (case-insensitive)
_HEADING_PATTERNS: list[tuple[str, re.Pattern]] = [
    (
        "preferred",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:preferred\s+(?:skills|qualifications|requirements)|nice[\s-]to[\s-]have|good[\s-]to[\s-]have|bonus\s+skills|desired\s+skills|bonus|optional\s+skills|plus\s+points)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "required",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:required\s+(?:skills|qualifications|requirements)|must[\s-]have|technical\s+requirements|core\s+requirements|minimum\s+qualifications|basic\s+qualifications|skills\s+required|requirements|what\s+we(?:'re|\s+are)?\s+looking\s+for)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "responsibilities",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:responsibilities|key\s+responsibilities|role\s+responsibilities|what\s+you(?:'ll|\s+will)\s+do|duties|job\s+description|about\s+the\s+role)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "qualifications",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:qualifications|education|eligibility|academic\s+qualifications|educational\s+requirements)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
    (
        "other",
        re.compile(
            r"^(?:[\d\.\*\-#]+\s*)?(?:benefits|perks|compensation|salary|about\s+us|who\s+we\s+are|how\s+to\s+apply|company\s+overview|equal\s+opportunity)[\s:\-]*$",
            re.IGNORECASE,
        ),
    ),
]


def _clean_bullet(line: str) -> str:
    """Remove leading bullet points, numbers, and whitespace from a line."""
    return re.sub(r"^[\s*•\-–—\d\.\)\:\?·]+", "", line).strip()


def _extract_bullets(text: str) -> list[str]:
    """Split section text into non-empty bullet points or sentences."""
    lines = text.splitlines()
    bullets: list[str] = []
    current_bullet: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current_bullet:
                bullets.append(" ".join(current_bullet))
                current_bullet = []
            continue

        # Check if line starts a new bullet
        if re.match(r"^[\s*•\-–—\d\.\)\:]+", line):
            if current_bullet:
                bullets.append(" ".join(current_bullet))
            current_bullet = [_clean_bullet(stripped)]
        else:
            if current_bullet:
                current_bullet.append(stripped)
            else:
                current_bullet = [stripped]

    if current_bullet:
        bullets.append(" ".join(current_bullet))

    return [b for b in bullets if b]


def _extract_role_title(lines: list[str]) -> str | None:
    """Extract role title from header lines."""
    for line in lines[:10]:
        # Explicit label: e.g. "Job Title: Full Stack Developer Intern"
        match = re.search(r"(?:job\s+title|role|position)\s*:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    # Look for role keywords in early lines before section headers
    title_keywords = [
        "developer", "engineer", "intern", "internship", "architect",
        "specialist", "designer", "analyst", "lead", "consultant",
        "full stack", "frontend", "backend", "software", "devops",
    ]
    for line in lines[:6]:
        cleaned = _clean_bullet(line)
        if any(kw in cleaned.lower() for kw in title_keywords) and len(cleaned) <= 80:
            # Avoid matching whole paragraphs or sentences
            if not cleaned.endswith(".") or len(cleaned.split()) <= 8:
                return cleaned

    # Fallback to first non-empty line if short enough
    for line in lines[:3]:
        cleaned = _clean_bullet(line)
        if 3 <= len(cleaned) <= 60 and not cleaned.endswith("."):
            return cleaned

    return None


def _extract_company(lines: list[str]) -> str | None:
    """Extract hiring company name from header lines."""
    for line in lines[:15]:
        match = re.search(r"(?:company|organization)\s*:\s*(.+)$", line, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        match_about = re.search(r"about\s+([A-Za-z0-9\s&.,'-]+?)(?:\s*[:\-]|$)", line, re.IGNORECASE)
        if match_about and len(match_about.group(1).split()) <= 4:
            return match_about.group(1).strip()

    return None


def extract_jd(raw_text: str) -> JobDescription:
    """Extract structured JobDescription from raw text deterministically.

    Args:
        raw_text: Cleaned text from the JD PDF.

    Returns:
        A validated JobDescription model with raw_text preserved.

    Raises:
        ValueError: If raw_text is empty or blank.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot extract JD from empty text.")

    lines = raw_text.splitlines()

    # Metadata extraction
    role_title = _extract_role_title(lines)
    company = _extract_company(lines)

    # Section segmentation
    sections: dict[str, list[str]] = {
        "required": [],
        "preferred": [],
        "responsibilities": [],
        "qualifications": [],
        "other": [],
        "header": [],
    }

    current_section = "header"

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        matched_section = None
        for sec_name, pattern in _HEADING_PATTERNS:
            if pattern.match(stripped):
                matched_section = sec_name
                break

        if matched_section:
            current_section = matched_section
        else:
            sections[current_section].append(line)

    # Required skills extraction
    required_text = "\n".join(sections["required"])
    required_skills = extract_skills_from_text(required_text)

    # If no separate required section was found, check qualifications or all text
    if not required_skills and sections["qualifications"]:
        qual_text = "\n".join(sections["qualifications"])
        required_skills = extract_skills_from_text(qual_text)

    # Preferred skills extraction
    preferred_text = "\n".join(sections["preferred"])
    preferred_skills = extract_skills_from_text(preferred_text)

    # Remove any overlap (required takes precedence)
    preferred_skills = [s for s in preferred_skills if s not in set(required_skills)]

    # Responsibilities extraction
    resp_text = "\n".join(sections["responsibilities"])
    responsibilities = _extract_bullets(resp_text)

    # Qualifications extraction
    qual_text = "\n".join(sections["qualifications"])
    qualifications = _extract_bullets(qual_text)

    # Normalize skills
    required_skills = normalize_skills(required_skills)
    preferred_skills = normalize_skills(preferred_skills)

    logger.info(
        "Extracted JD: title='%s', company='%s', required=%d, preferred=%d, resp=%d, qual=%d",
        role_title, company, len(required_skills), len(preferred_skills),
        len(responsibilities), len(qualifications),
    )

    return JobDescription(
        role_title=role_title,
        company=company,
        required_skills=required_skills,
        preferred_skills=preferred_skills,
        responsibilities=responsibilities,
        qualifications=qualifications,
        raw_text=raw_text,
    )
