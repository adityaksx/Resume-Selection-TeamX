"""Candidate Improvement Advisor with deterministic fallback (plan.md Phase 7E).

Provides actionable, constructive resume improvement recommendations for any candidate
evaluating against a target Job Description.
Distinguishes between "not found in resume" vs "candidate does not know this".
"""

from __future__ import annotations

import logging
from typing import Any

from app.llm.client import GeminiError, GeminiUnavailableError, generate_text, is_gemini_available
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult

logger = logging.getLogger(__name__)

IMPROVEMENT_SYSTEM_INSTRUCTION = """\
You are an expert career and technical resume advisor providing feedback on how a candidate can improve their resume for a specific job description.
Structure your recommendations into exactly four sections:
1. Priority Skill Gaps: Required skills from the JD not found in the resume.
2. Resume Evidence Gaps: Areas where qualifications or responsibilities in the JD lacked strong corresponding resume project/experience descriptions.
3. Project/Experience Opportunities: Concrete technical project ideas the candidate could build to demonstrate the missing competencies.
4. Recommended Next Steps: Practical advice on restructuring, detailing evidence, or acquiring certifications.

CRITICAL TONE AND ACCURACY RULES:
- Carefully distinguish between "not explicitly found in the resume" versus "you do not know this". Never assume a candidate lacks knowledge simply because it wasn't listed.
- Do NOT invent or hallucinate missing information. Ground your guidance strictly in the missing required and preferred competencies.
- Be encouraging, objective, and specific to the technical stack of the JD.
"""


def generate_deterministic_improvement_advice(
    candidate: CandidateResult,
    jd: JobDescription | None = None,
) -> str:
    """Generate rule-based improvement advice grounded in missing skills and scores."""
    lines = [
        f"### Resume Improvement Recommendations: {candidate.candidate_name}",
        f"**Target Role:** {jd.role_title if jd and jd.role_title else 'Target Job Description'}",
        f"**Current Scores:** Final: {candidate.final_score:.2f} | Keyword: {candidate.keyword_score:.2f} | Semantic: {candidate.semantic_score:.2f}",
        "",
        "#### 1. Priority Skill Gaps",
    ]

    if candidate.missing_required_skills:
        for skill in candidate.missing_required_skills:
            lines.append(f"- **{skill}:** This core required skill was not explicitly detected in the resume text. If you have experience with {skill}, make sure it is clearly listed under your Technical Skills section.")
    else:
        lines.append("- **Great work!** All core required skills were detected in your resume.")

    lines.append("")
    lines.append("#### 2. Resume Evidence Gaps")
    if candidate.semantic_score < 60.0:
        lines.append("- **Project Descriptions:** The semantic alignment score indicates that project and experience descriptions could more explicitly detail responsibilities and architectures matching the role.")
    else:
        lines.append("- **Strong Contextual Alignment:** Your project descriptions demonstrate solid relevance to the role's responsibilities.")

    if candidate.missing_preferred_skills:
        lines.append(f"- **Preferred Qualifications:** The following preferred skills were not found: {', '.join(candidate.missing_preferred_skills)}. Adding relevant coursework, projects, or certifications here can boost your competitiveness.")

    lines.append("")
    lines.append("#### 3. Project/Experience Opportunities")
    if candidate.missing_required_skills:
        lines.append(f"- Build an end-to-end portfolio project featuring {', '.join(candidate.missing_required_skills[:3])} to provide direct technical proof.")
    else:
        lines.append("- Add metrics and quantitative impact to existing projects (e.g. latency improvements, user scale, test coverage).")

    lines.append("")
    lines.append("#### 4. Recommended Next Steps")
    lines.append("1. **Update Keywords:** Ensure exact technical keywords match standard industry naming.")
    lines.append("2. **Highlight Quantifiable Achievements:** Detail specific technologies used in each bullet point under Experience and Projects.")
    lines.append("3. **Align Terminology:** Frame project descriptions around the core responsibilities outlined in the job description.")

    return "\n".join(lines)


def generate_candidate_improvement_advice(
    candidate: CandidateResult,
    jd: JobDescription | None = None,
    resume_context: str | None = None,
) -> str:
    """Generate candidate improvement advice via Gemini or deterministic fallback.

    Args:
        candidate: CandidateResult with scores and matched/missing skills.
        jd: Structured JobDescription.
        resume_context: Optional additional resume text excerpt.

    Returns:
        Structured improvement recommendations.
    """
    if not is_gemini_available():
        return generate_deterministic_improvement_advice(candidate, jd)

    jd_info = ""
    if jd:
        jd_info = f"""\
Target Role: {jd.role_title} ({jd.company})
Required Skills: {', '.join(jd.required_skills)}
Preferred Skills: {', '.join(jd.preferred_skills)}
Responsibilities: {'; '.join(jd.responsibilities[:3]) if jd.responsibilities else 'N/A'}
"""

    prompt = f"""\
{jd_info}

Candidate Information:
- Name: {candidate.candidate_name}
- Final Score: {candidate.final_score:.2f} / 100
- Keyword Score: {candidate.keyword_score:.2f} / 100
- Semantic Score: {candidate.semantic_score:.2f} / 100
- Matched Required Skills: {', '.join(candidate.matched_required_skills) if candidate.matched_required_skills else 'None'}
- Missing Required Skills: {', '.join(candidate.missing_required_skills) if candidate.missing_required_skills else 'None'}
- Matched Preferred Skills: {', '.join(candidate.matched_preferred_skills) if candidate.matched_preferred_skills else 'None'}
- Missing Preferred Skills: {', '.join(candidate.missing_preferred_skills) if candidate.missing_preferred_skills else 'None'}

Please provide targeted, actionable improvement advice structured into the four designated sections.
"""

    try:
        return generate_text(prompt=prompt, system_instruction=IMPROVEMENT_SYSTEM_INSTRUCTION)
    except (GeminiUnavailableError, GeminiError) as exc:
        logger.warning("AI improvement advice generation failed: %s. Using deterministic fallback.", exc)
        return generate_deterministic_improvement_advice(candidate, jd)
