"""Deterministic explanation generator for Top-3 candidates (plan.md §15).

Generates transparent, rule-based explanations strictly from stored evidence:
keyword matches, missing skills, semantic similarity, and requirement-level evidence chunks.
Strictly NO generative LLMs or external APIs are used.
"""

from __future__ import annotations

import logging
from typing import Any

from app.models.result_models import CandidateResult, RankingResult

logger = logging.getLogger(__name__)


def _format_skill_list(skills: list[str], default_text: str = "None") -> str:
    """Format a list of skills as a comma-separated string or return a default fallback."""
    if not skills:
        return default_text
    return ", ".join(skills)


def select_top_semantic_evidence(
    semantic_evidence: list[dict[str, Any]],
    top_k: int = 3,
    min_similarity: float = 0.0,
) -> list[dict[str, Any]]:
    """Sort and filter the strongest requirement-level semantic evidence matches.

    Args:
        semantic_evidence: List of requirement match dictionaries.
        top_k: Maximum number of evidence items to retain (default: 3).
        min_similarity: Minimum similarity (0.0 to 1.0) threshold to consider meaningful.

    Returns:
        Top-k evidence matches sorted by similarity descending.
    """
    if not semantic_evidence:
        return []

    valid_matches: list[dict[str, Any]] = []
    for ev in semantic_evidence:
        if not isinstance(ev, dict):
            continue
        req = ev.get("requirement", "").strip()
        evidence_text = ev.get("best_matching_evidence", "").strip()
        sim = float(ev.get("similarity", 0.0))

        # Only retain evidence if requirement is present and similarity meets threshold
        if req and evidence_text and sim >= min_similarity:
            valid_matches.append(ev)

    # Sort descending by similarity
    sorted_matches = sorted(
        valid_matches,
        key=lambda x: float(x.get("similarity", 0.0)),
        reverse=True,
    )
    return sorted_matches[:top_k]


def build_why_ranked_highly_bullet_points(candidate: CandidateResult) -> list[str]:
    """Generate factual, evidence-grounded bullet points explaining candidate ranking.

    Never generates unfounded qualitative claims like 'perfect candidate' or 'guaranteed fit'.
    All bullets are deterministically constructed from candidate scores, skill counts, and evidence.
    """
    bullets: list[str] = []

    num_matched_req = len(candidate.matched_required_skills)
    num_missing_req = len(candidate.missing_required_skills)
    total_req = num_matched_req + num_missing_req

    # 1. Required skill coverage
    if total_req > 0:
        match_pct = (num_matched_req / total_req) * 100.0
        if num_missing_req == 0:
            bullets.append(f"Matches all {total_req} of {total_req} required skills (100.0%).")
        else:
            bullets.append(f"Matches {num_matched_req} of {total_req} required skills ({match_pct:.1f}%).")
    elif num_matched_req > 0:
        bullets.append(f"Matches {num_matched_req} required skills.")

    # 2. Key explicit matches
    if candidate.matched_required_skills:
        skills_preview = ", ".join(candidate.matched_required_skills[:6])
        if len(candidate.matched_required_skills) > 6:
            skills_preview += f", and {len(candidate.matched_required_skills) - 6} more"
        bullets.append(f"Explicit required skill matches: {skills_preview}.")

    # 3. Missing skills impact if any
    if candidate.missing_required_skills:
        missing_preview = ", ".join(candidate.missing_required_skills[:4])
        bullets.append(f"Missing required skills: {missing_preview}.")

    # 4. Keyword score
    bullets.append(f"Keyword score is {candidate.keyword_score:.2f}/100 based on explicit skill and alias matching.")

    # 5. Semantic similarity score
    bullets.append(
        f"Semantic similarity score is {candidate.semantic_score:.2f}/100 across requirement descriptions."
    )

    # 6. Preferred skills bonus if matched
    if candidate.matched_preferred_skills:
        pref_preview = ", ".join(candidate.matched_preferred_skills[:4])
        bullets.append(f"Demonstrates preferred qualifications: {pref_preview}.")

    return bullets


def generate_candidate_explanation(candidate: CandidateResult) -> str:
    """Generate a transparent, deterministic explanation for a ranked candidate.

    The explanation is generated strictly from the candidate's scores, matched/missing
    skills, and requirement-level semantic evidence.

    Args:
        candidate: CandidateResult containing scores and evidence.

    Returns:
        Structured explanation string formatted in clean markdown.
    """
    lines: list[str] = []

    # Header & Scores
    lines.append(f"Candidate: {candidate.candidate_name}")
    lines.append(f"Final Score: {candidate.final_score:.2f} / 100")
    lines.append(f"Keyword Score: {candidate.keyword_score:.2f} / 100 | Semantic Score: {candidate.semantic_score:.2f} / 100")
    lines.append("")

    # Why the candidate ranked highly
    lines.append("Why this candidate ranked highly:")
    bullets = build_why_ranked_highly_bullet_points(candidate)
    if bullets:
        for b in bullets:
            lines.append(f"- {b}")
    else:
        lines.append("- Evaluated against configured keyword and semantic criteria.")
    lines.append("")

    # Skill Breakdowns
    lines.append("Matched required skills:")
    lines.append(_format_skill_list(candidate.matched_required_skills, default_text="None"))
    lines.append("")

    lines.append("Missing required skills:")
    lines.append(_format_skill_list(candidate.missing_required_skills, default_text="None (all required skills matched)"))
    lines.append("")

    lines.append("Preferred skills matched:")
    lines.append(_format_skill_list(candidate.matched_preferred_skills, default_text="None"))
    lines.append("")

    lines.append("Preferred skills missing:")
    lines.append(_format_skill_list(candidate.missing_preferred_skills, default_text="None"))
    lines.append("")

    # Strong Semantic Evidence
    lines.append("Strong semantic evidence:")
    top_evidence = select_top_semantic_evidence(candidate.semantic_evidence, top_k=3, min_similarity=0.1)

    if top_evidence:
        for ev in top_evidence:
            req = ev.get("requirement", "").strip()
            text = ev.get("best_matching_evidence", "").strip()
            sim_score = ev.get("similarity_score")
            if sim_score is None:
                sim_score = round(float(ev.get("similarity", 0.0)) * 100.0, 1)

            lines.append(f"- JD Requirement: \"{req}\"")
            lines.append(f"  Resume Evidence: \"{text}\"")
            lines.append(f"  Similarity: {sim_score:.1f}%")
    else:
        lines.append("No strong semantic evidence recorded.")

    return "\n".join(lines)


def attach_top_explanations(
    ranking: RankingResult,
    top_k: int = 3,
) -> RankingResult:
    """Generate and attach deterministic explanations for the top-k ranked candidates.

    Candidates ranked beyond top_k have their explanation set to None to avoid
    wasteful processing while keeping all candidate scores and rankings unchanged.

    Args:
        ranking: RankingResult containing ordered candidates.
        top_k: Number of top positions to generate explanations for (default: 3).

    Returns:
        Updated RankingResult with explanations attached to top_k candidates.
    """
    if not ranking.candidates:
        return ranking

    updated_candidates: list[CandidateResult] = []
    for idx, cand in enumerate(ranking.candidates):
        # 1-indexed rank position: ranks 1..top_k receive explanations
        if idx < top_k:
            explanation = generate_candidate_explanation(cand)
            cand_copy = cand.model_copy(update={"explanation": explanation})
            updated_candidates.append(cand_copy)
        else:
            # Candidates below top_k preserve existing None explanation
            cand_copy = cand.model_copy(update={"explanation": None})
            updated_candidates.append(cand_copy)

    logger.info(
        "Generated and attached explanations for top %d candidates out of %d.",
        min(top_k, len(updated_candidates)),
        len(updated_candidates),
    )
    return RankingResult(
        jd_role_title=ranking.jd_role_title,
        candidates=updated_candidates,
    )
