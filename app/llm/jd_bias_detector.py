"""Job Description Fairness and Narrow-Language Analysis (plan.md Phase 7G).

Analyzes job descriptions for subjective phrasing, unnecessary tool constraints,
and exclusionary language. Acts purely as an advisory reviewer and never alters rankings.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from app.llm.client import GeminiError, GeminiUnavailableError, generate_text, is_gemini_available
from app.models.fairness_models import FairnessFinding, JDFairnessReport
from app.models.jd_models import JobDescription

logger = logging.getLogger(__name__)

FAIRNESS_SYSTEM_INSTRUCTION = """\
You are an expert recruitment diversity, equity, and inclusion advisor reviewing a Job Description.
Analyze the JD for:
1. Subjective wording (e.g. "rockstar", "ninja", "cultural fit")
2. Unnecessarily narrow requirements or rigid tech stack constraints where general software knowledge suffices
3. Unnecessarily restrictive qualifications (e.g. requiring a specific degree when equivalent experience works)
4. Potentially exclusionary or biased language (e.g. age-coded, gender-coded, or background-exclusionary phrasing)

OUTPUT FORMAT REQUIREMENTS:
You must respond with valid JSON matching this structure:
{
  "overall_summary": "Brief 1-2 sentence assessment of the JD's inclusivity and clarity.",
  "findings": [
    {
      "phrase": "exact or summarized phrase from JD",
      "issue": "Category: Subjective Phrasing | Narrow Requirement | Restrictive Qualification | Exclusionary Language",
      "rationale": "Clear explanation of why this might restrict candidate diversity",
      "suggested_alternative": "Inclusive, capability-oriented replacement phrasing"
    }
  ]
}
Do NOT claim legal violations. Label every item as an advisory recommendation for human review.
"""

# Deterministic rule-based dictionary of common problematic hiring phrasing
HEURISTIC_PATTERNS = [
    (
        r"\b(?:rockstar|ninja|guru|wizard|superhero)\b",
        "Subjective Phrasing",
        "Jargon terms like 'ninja' or 'rockstar' are vague and disproportionately discourage qualified underrepresented applicants.",
        "experienced and collaborative developer",
    ),
    (
        r"\b(?:young and energetic|digital native|recent graduate[s]? only)\b",
        "Age-Coded Language",
        "Terms emphasizing youth or graduation dates may discourage experienced applicants and create unintentional age bias.",
        "motivated learner eager to build scalable web applications",
    ),
    (
        r"\b(?:native English speaker|fluent English without accent)\b",
        "Potentially Exclusionary Language",
        "Requiring 'native' English rather than professional working proficiency can exclude qualified international candidates.",
        "strong written and verbal communication skills in English",
    ),
    (
        r"\b(?:top[- ]tier (?:university|college)|tier[- ]1 college|ivy league)\b",
        "Socioeconomic / Institutional Restriction",
        "Restricting applicants to elite institutions filters out exceptional self-taught or non-traditional candidates.",
        "degree in Computer Science, related field, or equivalent practical project experience",
    ),
    (
        r"\b(?:work hard play hard|24/7 availability|round-the-clock)\b",
        "Work-Life Balance Concerns",
        "May discourage candidates with caregiving responsibilities or commitments outside of standard working hours.",
        "ability to prioritize deliverables during core collaborative working hours",
    ),
]


def run_deterministic_fairness_scan(jd: JobDescription) -> JDFairnessReport:
    """Perform rule-based regex scan across JD text for common narrow or biased phrasing."""
    findings: list[FairnessFinding] = []
    text_corpus = f"{jd.raw_text} {' '.join(jd.responsibilities)} {' '.join(jd.qualifications)}"

    for pattern, issue, rationale, alternative in HEURISTIC_PATTERNS:
        match = re.search(pattern, text_corpus, re.IGNORECASE)
        if match:
            findings.append(
                FairnessFinding(
                    phrase=match.group(0),
                    issue=issue,
                    rationale=rationale,
                    suggested_alternative=alternative,
                )
            )

    # Check for excessive required skills (e.g. > 8 required skills for an intern role)
    if "intern" in (jd.role_title or "").lower() and len(jd.required_skills) > 7:
        findings.append(
            FairnessFinding(
                phrase=f"{len(jd.required_skills)} required skills listed for an intern role",
                issue="Potentially Over-Constrained Requirements",
                rationale="Listing extensive required skills for an internship position may discourage candidates with strong foundational abilities who haven't yet worked across all specific tools.",
                suggested_alternative="Keep core required skills to 3-4 fundamentals, moving specialized tools to preferred qualifications.",
            )
        )

    summary = (
        f"Found {len(findings)} potential phrasing considerations for human review."
        if findings
        else "The job description uses clear, objective, and capability-focused language."
    )

    return JDFairnessReport(
        role_title=jd.role_title or "Job Description",
        findings=findings,
        overall_summary=summary,
    )


def analyze_jd_fairness(jd: JobDescription) -> JDFairnessReport:
    """Analyze JD fairness and narrow requirements using Gemini with deterministic fallback.

    Args:
        jd: Structured JobDescription.

    Returns:
        Populated JDFairnessReport.
    """
    if not is_gemini_available():
        return run_deterministic_fairness_scan(jd)

    prompt = f"""\
Job Title: {jd.role_title}
Company: {jd.company}

Required Skills: {', '.join(jd.required_skills)}
Preferred Skills: {', '.join(jd.preferred_skills)}

Responsibilities:
{chr(10).join(f'- {r}' for r in jd.responsibilities)}

Qualifications:
{chr(10).join(f'- {q}' for q in jd.qualifications)}

Full JD Text:
{jd.raw_text[:2500]}

Please analyze this job description for subjective phrasing, restrictive criteria, and opportunities to improve applicant pool diversity. Return valid JSON.
"""

    try:
        raw_output = generate_text(prompt=prompt, system_instruction=FAIRNESS_SYSTEM_INSTRUCTION)
        # Clean potential markdown code fences ```json ... ```
        cleaned_json = raw_output.strip()
        if cleaned_json.startswith("```"):
            cleaned_json = re.sub(r"^```(?:json)?\n?", "", cleaned_json)
            cleaned_json = re.sub(r"\n?```$", "", cleaned_json)

        parsed = json.loads(cleaned_json)
        findings: list[FairnessFinding] = []
        for f in parsed.get("findings", []):
            findings.append(
                FairnessFinding(
                    phrase=f.get("phrase", ""),
                    issue=f.get("issue", "Subjective Phrasing"),
                    rationale=f.get("rationale", ""),
                    suggested_alternative=f.get("suggested_alternative", ""),
                )
            )

        return JDFairnessReport(
            role_title=jd.role_title or "Job Description",
            findings=findings,
            overall_summary=parsed.get("overall_summary", "Review completed."),
        )

    except Exception as exc:
        logger.warning("AI JD fairness check failed: %s. Falling back to deterministic scan.", exc)
        return run_deterministic_fairness_scan(jd)
