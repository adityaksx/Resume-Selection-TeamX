"""Top-3 AI Explanation Generator with deterministic fallback (plan.md Phase 7C).

Generates natural language explanations for top-ranked candidates using Gemini,
grounded strictly in stored scores, skill matches, and semantic evidence.
If Gemini is unavailable or fails, automatically falls back to the deterministic
explanation generator.
"""

from __future__ import annotations

import logging
from typing import Any

from app.explanation.explanation_generator import (
    generate_candidate_explanation as generate_deterministic_explanation,
    select_top_semantic_evidence,
)
from app.llm.client import GeminiError, GeminiUnavailableError, generate_text, is_gemini_available
from app.models.result_models import CandidateResult, RankingResult

logger = logging.getLogger(__name__)

TOP3_SYSTEM_INSTRUCTION = """\
You are an expert technical recruiter assistant explaining why a candidate ranked in the top 3 shortlist for a role.
Your explanation must be strictly grounded in the provided candidate evidence:
- Explain why the candidate achieved their ranking position based on their matched skills and semantic evidence.
- Highlight key technical strengths with concrete project/experience evidence from the resume.
- Factual and objective: explicitly note any missing required skills or gaps.
- Strictly forbidden:
  - Do NOT invent or assume skills, technologies, or experience not explicitly listed.
  - Do NOT recalculate or suggest altering any scores or rankings.
  - Do NOT use vague superlatives like "perfect candidate" or "guaranteed fit".
Keep the summary structured, professional, and concise (around 3-4 paragraphs or clear bulleted sections).
"""


def format_evidence_for_llm(candidate: CandidateResult) -> str:
    """Format structured candidate evidence into a clean LLM prompt payload."""
    lines = [
        f"Candidate Name: {candidate.candidate_name}",
        f"Shortlist Rank: #{candidate.rank}",
        f"Final Score: {candidate.final_score:.2f} / 100",
        f"Keyword Score: {candidate.keyword_score:.2f} / 100",
        f"Semantic Score: {candidate.semantic_score:.2f} / 100",
        "",
        f"Matched Required Skills ({len(candidate.matched_required_skills)}): "
        + (", ".join(candidate.matched_required_skills) if candidate.matched_required_skills else "None"),
        f"Missing Required Skills ({len(candidate.missing_required_skills)}): "
        + (", ".join(candidate.missing_required_skills) if candidate.missing_required_skills else "None"),
        f"Matched Preferred Skills ({len(candidate.matched_preferred_skills)}): "
        + (", ".join(candidate.matched_preferred_skills) if candidate.matched_preferred_skills else "None"),
        f"Missing Preferred Skills ({len(candidate.missing_preferred_skills)}): "
        + (", ".join(candidate.missing_preferred_skills) if candidate.missing_preferred_skills else "None"),
        "",
        "Strongest Semantic Evidence Matches (Cosine Similarity):",
    ]

    top_evidence = select_top_semantic_evidence(candidate.semantic_evidence, top_k=3, min_similarity=0.1)
    if top_evidence:
        for ev in top_evidence:
            req = ev.get("requirement", "")
            evidence_text = ev.get("best_matching_evidence", "")
            sim_score = ev.get("similarity_score", round(float(ev.get("similarity", 0.0)) * 100.0, 1))
            lines.append(f"- Requirement: \"{req}\"")
            lines.append(f"  Resume Evidence: \"{evidence_text}\"")
            lines.append(f"  Similarity: {sim_score:.1f}%")
    else:
        lines.append("- No strong requirement-level semantic evidence recorded.")

    lines.append("\nPlease generate an explainable summary for why this candidate ranked highly.")
    return "\n".join(lines)


def generate_ai_candidate_explanation(candidate: CandidateResult) -> str:
    """Generate an AI explanation for a candidate, falling back to deterministic if unavailable.

    Args:
        candidate: Scored CandidateResult object.

    Returns:
        Natural language explanation string.
    """
    if not is_gemini_available():
        logger.debug("Gemini unavailable; using deterministic explanation for %s", candidate.candidate_name)
        return generate_deterministic_explanation(candidate)

    prompt = format_evidence_for_llm(candidate)
    try:
        explanation = generate_text(prompt=prompt, system_instruction=TOP3_SYSTEM_INSTRUCTION)
        return explanation
    except (GeminiUnavailableError, GeminiError) as exc:
        logger.warning(
            "Gemini explanation generation failed for '%s': %s. Falling back to deterministic template.",
            candidate.candidate_name,
            exc,
        )
        return generate_deterministic_explanation(candidate)


def attach_top_ai_explanations(
    ranking: RankingResult,
    top_k: int = 3,
    force_deterministic: bool = False,
) -> RankingResult:
    """Attach AI or deterministic explanations to top_k candidates.

    Candidates beyond top_k have explanation=None.
    Never alters ranking order or candidate scores.

    Args:
        ranking: Ordered RankingResult.
        top_k: Number of top positions to explain (default: 3).
        force_deterministic: If True, bypasses LLM and uses deterministic generator.

    Returns:
        Updated RankingResult with explanations attached to top_k candidates.
    """
    if not ranking.candidates:
        return ranking

    updated: list[CandidateResult] = []
    for idx, cand in enumerate(ranking.candidates):
        if idx < top_k:
            if force_deterministic or not is_gemini_available():
                expl = generate_deterministic_explanation(cand)
            else:
                expl = generate_ai_candidate_explanation(cand)
            updated.append(cand.model_copy(update={"explanation": expl}))
        else:
            updated.append(cand.model_copy(update={"explanation": None}))

    return RankingResult(
        jd_role_title=ranking.jd_role_title,
        candidates=updated,
    )
