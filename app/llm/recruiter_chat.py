"""Recruiter AI Chat Service (plan.md Phase 7F).

Empowers hiring managers and recruiters to ask natural-language questions
about the active candidate shortlist, rankings, skill gaps, and interview prep.
Grounded strictly in structured shortlist evidence; never overrides rankings or scores.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from app.llm.client import GeminiError, GeminiUnavailableError, generate_text, is_gemini_available
from app.models.jd_models import JobDescription
from app.models.result_models import CandidateResult, RankingResult

logger = logging.getLogger(__name__)

RECRUITER_CHAT_SYSTEM_INSTRUCTION = """\
You are an expert technical recruiting assistant grounded strictly in the current resume shortlisting results.
Your source of truth is the provided shortlist data: candidate ranks, final scores, keyword scores, semantic scores, matched skills, missing skills, and semantic evidence.

RULES:
1. Grounding: Answer questions using ONLY the provided candidate data and job description. Never invent skills, companies, scores, or achievements not in the context.
2. Ranking Authority: The candidate ranking and scores were calculated by a deterministic scoring engine and are final. Do NOT recalculate or suggest overriding the ranking.
3. Ambiguity Handling: If the user mentions an ambiguous candidate (e.g. "Candidate A" when no candidate has that name, or multiple candidates share a first name), politely ask for clarification rather than guessing.
4. Professional Recruiter Tone: Be concise, clear, and actionable. Provide specific comparisons, interview questions, and skill breakdowns when requested.
"""


def resolve_candidate_references(
    query: str,
    candidates: list[CandidateResult],
) -> list[CandidateResult]:
    """Identify candidate(s) referenced in a recruiter query by name, rank, or filename.

    Args:
        query: User message text.
        candidates: List of CandidateResult objects.

    Returns:
        List of uniquely matched CandidateResult objects.
    """
    matched: list[CandidateResult] = []
    seen_names: set[str] = set()
    query_lower = query.lower()

    # 1. Match by rank pattern: #1, rank 1, candidate 1, number 2, top candidate
    rank_matches = re.findall(r"(?:#|rank\s*|candidate\s*|no\.?\s*)(\d+)", query_lower)
    for r_str in rank_matches:
        try:
            r_num = int(r_str)
            for c in candidates:
                if c.rank == r_num and c.candidate_name not in seen_names:
                    matched.append(c)
                    seen_names.add(c.candidate_name)
        except ValueError:
            pass

    if "top candidate" in query_lower or "winner" in query_lower or "first candidate" in query_lower:
        if candidates and candidates[0].candidate_name not in seen_names:
            matched.append(candidates[0])
            seen_names.add(candidates[0].candidate_name)

    # 2. Match by full name or distinct name tokens
    for c in candidates:
        name_lower = c.candidate_name.lower()
        # Full name match
        if name_lower in query_lower and c.candidate_name not in seen_names:
            matched.append(c)
            seen_names.add(c.candidate_name)
            continue

        # First name match (if length >= 3 and not ambiguous)
        first_name = name_lower.split()[0] if name_lower else ""
        if len(first_name) >= 3 and re.search(rf"\b{re.escape(first_name)}\b", query_lower):
            # Ensure first name is not shared by another candidate
            matches_with_first = [other for other in candidates if other.candidate_name.lower().startswith(first_name)]
            if len(matches_with_first) == 1 and c.candidate_name not in seen_names:
                matched.append(c)
                seen_names.add(c.candidate_name)

    return matched


def build_shortlist_context(
    ranking: RankingResult,
    jd: JobDescription | None = None,
    referenced_candidates: list[CandidateResult] | None = None,
) -> str:
    """Build a comprehensive context payload for the chat model."""
    lines = ["=== SHORTLIST CONTEXT ==="]
    if jd:
        lines.append(f"Role: {jd.role_title} at {jd.company}")
        lines.append(f"Required Skills: {', '.join(jd.required_skills)}")
        lines.append(f"Preferred Skills: {', '.join(jd.preferred_skills)}")
        lines.append("")

    lines.append(f"Total Candidates Processed: {len(ranking.candidates)}")
    lines.append("Shortlist Overview (Ranked by Final Score = 50% Keyword + 50% Semantic):")
    for c in ranking.candidates:
        lines.append(
            f"#{c.rank} {c.candidate_name} | Final: {c.final_score:.2f} | Keyword: {c.keyword_score:.2f} | Semantic: {c.semantic_score:.2f} | Matched Req: {len(c.matched_required_skills)} | Missing Req: {len(c.missing_required_skills)}"
        )
    lines.append("")

    # Detailed data for referenced candidates or top 3 if none referenced
    targets = referenced_candidates if referenced_candidates else ranking.candidates[:3]
    if targets:
        lines.append("Detailed Evidence for Relevant Candidates:")
        for c in targets:
            lines.append(f"--- Candidate #{c.rank}: {c.candidate_name} ---")
            lines.append(f"Matched Required Skills: {', '.join(c.matched_required_skills) if c.matched_required_skills else 'None'}")
            lines.append(f"Missing Required Skills: {', '.join(c.missing_required_skills) if c.missing_required_skills else 'None'}")
            lines.append(f"Matched Preferred Skills: {', '.join(c.matched_preferred_skills) if c.matched_preferred_skills else 'None'}")
            lines.append(f"Missing Preferred Skills: {', '.join(c.missing_preferred_skills) if c.missing_preferred_skills else 'None'}")
            if c.semantic_evidence:
                top_ev = c.semantic_evidence[:2]
                for ev in top_ev:
                    lines.append(f"  * Evidence for '{ev.get('requirement')}': \"{ev.get('best_matching_evidence')}\" ({ev.get('similarity_score', round(float(ev.get('similarity', 0))*100, 1))}%)")

    return "\n".join(lines)


def chat_with_recruiter(
    message: str,
    history: list[dict[str, str]],
    ranking: RankingResult,
    jd: JobDescription | None = None,
) -> str:
    """Process a recruiter chat question and return an evidence-grounded response.

    Args:
        message: Current user query.
        history: List of previous conversation turns [{"role": "user"|"assistant", "content": str}].
        ranking: Active RankingResult.
        jd: Structured JobDescription.

    Returns:
        Chat response string.
    """
    if not ranking.candidates:
        return "No candidate shortlist is currently active. Please upload a JD and resumes first."

    referenced = resolve_candidate_references(message, ranking.candidates)
    context_payload = build_shortlist_context(ranking, jd, referenced_candidates=referenced)

    if not is_gemini_available():
        # Fallback deterministic answer for common queries
        msg_lower = message.lower()
        if referenced:
            c = referenced[0]
            if "missing" in msg_lower or "lack" in msg_lower:
                missing = ", ".join(c.missing_required_skills) if c.missing_required_skills else "None (all matched!)"
                return f"#{c.rank} {c.candidate_name} is missing the following required skills: **{missing}**."
            elif "why" in msg_lower and ("rank" in msg_lower or "score" in msg_lower):
                return (
                    f"#{c.rank} {c.candidate_name} scored **{c.final_score:.2f} / 100** (Keyword: {c.keyword_score:.2f}, Semantic: {c.semantic_score:.2f}). "
                    f"They matched {len(c.matched_required_skills)} required skills ({', '.join(c.matched_required_skills)})."
                )

        if len(referenced) >= 2:
            a, b = referenced[0], referenced[1]
            diff = a.final_score - b.final_score
            higher = a if diff >= 0 else b
            lower = b if diff >= 0 else a
            return (
                f"**{higher.candidate_name}** (#{higher.rank}, Score: {higher.final_score:.2f}) is ranked above "
                f"**{lower.candidate_name}** (#{lower.rank}, Score: {lower.final_score:.2f}) by a margin of {abs(diff):.2f} points. "
                f"{higher.candidate_name} matched {len(higher.matched_required_skills)} required skills versus {len(lower.matched_required_skills)} for {lower.candidate_name}."
            )

        return (
            "*(Deterministic Response)* Shortlist contains "
            f"{len(ranking.candidates)} candidates. Top candidate is #{ranking.candidates[0].rank} "
            f"{ranking.candidates[0].candidate_name} (Score: {ranking.candidates[0].final_score:.2f}). "
            "To unlock full conversational AI chat, configure `GEMINI_API_KEY`."
        )

    # Format full prompt with conversation history
    history_formatted: list[str] = []
    for turn in history[-6:]:  # Keep recent history
        role = "Recruiter" if turn["role"] == "user" else "Assistant"
        history_formatted.append(f"{role}: {turn['content']}")

    history_text = "\n".join(history_formatted)

    full_prompt = f"""\
{context_payload}

=== CONVERSATION HISTORY ===
{history_text}

Recruiter: {message}
Assistant:"""

    try:
        return generate_text(prompt=full_prompt, system_instruction=RECRUITER_CHAT_SYSTEM_INSTRUCTION)
    except (GeminiUnavailableError, GeminiError) as exc:
        logger.warning("Recruiter chat LLM generation failed: %s", exc)
        return f"Unable to process chat request via Gemini ({exc}). Please check your API key."
