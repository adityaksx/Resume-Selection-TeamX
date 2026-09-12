"""AI and deterministic comparison explanation between two candidates (plan.md Phase 7D).

Explains side-by-side strengths, skill coverage differences, and scoring nuances
without picking or modifying the winner.
"""

from __future__ import annotations

import logging

from app.llm.client import GeminiError, GeminiUnavailableError, generate_text, is_gemini_available
from app.models.comparison_models import CandidateComparison

logger = logging.getLogger(__name__)

COMPARISON_SYSTEM_INSTRUCTION = """\
You are an expert technical recruiting analyst comparing two candidates who have been ranked by a shortlisting engine.
Your task is to provide an objective, evidence-based comparison explaining the differences between them.
Rules:
- The winner / higher-ranked candidate is ALREADY determined by the shortlisting engine based on objective metrics. Do NOT choose or modify the winner.
- Explain the key reasons behind the score differences:
  - Required skills matched vs missing
  - Relevant project and experience evidence
  - Keyword and semantic score contributions
- Factual and objective: use only the supplied candidate data. Do not assume or fabricate unlisted experience.
- Keep the explanation clear, professional, and directly actionable for a hiring manager.
"""


def generate_deterministic_comparison_summary(comp: CandidateComparison) -> str:
    """Generate a clean rule-based text summary of the comparison."""
    a = comp.candidate_a
    b = comp.candidate_b

    higher = comp.higher_ranked_candidate
    lower = b.candidate_name if higher == a.candidate_name else a.candidate_name

    lines = [
        f"### Comparison: {a.candidate_name} vs {b.candidate_name}",
        f"- **Higher Ranked:** {higher} (Rank #{min(a.rank or 99, b.rank or 99)})",
        f"- **Final Score Delta:** {abs(comp.final_score_difference):.2f} points",
        f"- **Keyword Score Delta:** {abs(comp.keyword_score_difference):.2f} points",
        f"- **Semantic Score Delta:** {abs(comp.semantic_score_difference):.2f} points",
        "",
        "#### Key Skill Differentiators:",
    ]

    if comp.unique_required_a:
        lines.append(f"- **Skills unique to {a.candidate_name}:** {', '.join(comp.unique_required_a)}")
    if comp.unique_required_b:
        lines.append(f"- **Skills unique to {b.candidate_name}:** {', '.join(comp.unique_required_b)}")
    if comp.shared_required_skills:
        lines.append(f"- **Shared matched skills:** {', '.join(comp.shared_required_skills)}")

    if comp.unique_missing_a:
        lines.append(f"- **Skills {a.candidate_name} lacks that {b.candidate_name} possesses:** {', '.join(comp.unique_missing_a)}")
    if comp.unique_missing_b:
        lines.append(f"- **Skills {b.candidate_name} lacks that {a.candidate_name} possesses:** {', '.join(comp.unique_missing_b)}")

    lines.append("")
    lines.append(
        f"**Summary:** {higher} holds the higher ranking primarily due to "
        f"{'stronger explicit required skill coverage' if abs(comp.keyword_score_difference) > abs(comp.semantic_score_difference) else 'higher semantic alignment with role responsibilities'}."
    )
    return "\n".join(lines)


def explain_comparison_with_ai(comp: CandidateComparison) -> str:
    """Generate an AI-assisted explanation of the candidate comparison with deterministic fallback.

    Args:
        comp: Populated CandidateComparison model.

    Returns:
        Explanation string.
    """
    if not is_gemini_available():
        return generate_deterministic_comparison_summary(comp)

    a = comp.candidate_a
    b = comp.candidate_b

    prompt = f"""\
Candidate Comparison Data:
- Candidate A: {a.candidate_name} (Rank #{a.rank}, Final Score: {a.final_score:.2f}, Keyword: {a.keyword_score:.2f}, Semantic: {a.semantic_score:.2f})
  - Matched Required Skills: {', '.join(a.matched_required_skills) if a.matched_required_skills else 'None'}
  - Missing Required Skills: {', '.join(a.missing_required_skills) if a.missing_required_skills else 'None'}
  - Matched Preferred Skills: {', '.join(a.matched_preferred_skills) if a.matched_preferred_skills else 'None'}

- Candidate B: {b.candidate_name} (Rank #{b.rank}, Final Score: {b.final_score:.2f}, Keyword: {b.keyword_score:.2f}, Semantic: {b.semantic_score:.2f})
  - Matched Required Skills: {', '.join(b.matched_required_skills) if b.matched_required_skills else 'None'}
  - Missing Required Skills: {', '.join(b.missing_required_skills) if b.missing_required_skills else 'None'}
  - Matched Preferred Skills: {', '.join(b.matched_preferred_skills) if b.matched_preferred_skills else 'None'}

Key Deltas:
- Higher Ranked Candidate: {comp.higher_ranked_candidate}
- Final Score Difference: {comp.final_score_difference:+.2f} points
- Keyword Score Difference: {comp.keyword_score_difference:+.2f} points
- Semantic Score Difference: {comp.semantic_score_difference:+.2f} points
- Shared Required Skills: {', '.join(comp.shared_required_skills) if comp.shared_required_skills else 'None'}
- Unique Required for A: {', '.join(comp.unique_required_a) if comp.unique_required_a else 'None'}
- Unique Required for B: {', '.join(comp.unique_required_b) if comp.unique_required_b else 'None'}

Please provide a structured, recruiter-friendly explanation of why {comp.higher_ranked_candidate} is ranked higher and how their profiles compare.
"""

    try:
        return generate_text(prompt=prompt, system_instruction=COMPARISON_SYSTEM_INSTRUCTION)
    except (GeminiUnavailableError, GeminiError) as exc:
        logger.warning("AI comparison explanation failed: %s. Using deterministic summary.", exc)
        return generate_deterministic_comparison_summary(comp)
