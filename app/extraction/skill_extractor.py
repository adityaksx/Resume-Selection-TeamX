"""Deterministic skill extraction using spaCy PhraseMatcher and RapidFuzz normalization."""

from __future__ import annotations

import re
from functools import lru_cache
from typing import Sequence

import spacy
from spacy.matcher import PhraseMatcher
from spacy.util import filter_spans

from app.matching.skill_normalizer import SKILL_ALIASES, normalize_skill, normalize_skills

# Common stop-words or false positives to avoid treating as skills
_FALSE_POSITIVES = {
    "and", "or", "the", "with", "for", "to", "in", "on", "at", "a", "an",
    "is", "are", "as", "by", "of", "all", "etc", "using", "experience",
    "proficient", "strong", "knowledge", "familiar", "skilled", "working",
    "understanding", "hands-on", "basic", "good", "excellent", "years",
}


@lru_cache(maxsize=1)
def _get_nlp_and_matcher():
    """Lazily initialize spaCy blank English pipeline and PhraseMatcher."""
    nlp = spacy.blank("en")
    matcher = PhraseMatcher(nlp.vocab, attr="LOWER")

    # Collect all known skill terms (both alias keys and canonical names)
    terms = set(SKILL_ALIASES.keys())
    for canonical in SKILL_ALIASES.values():
        terms.add(canonical.lower())

    patterns = [nlp.make_doc(term) for term in sorted(terms) if term.strip()]
    matcher.add("SKILL", patterns)
    return nlp, matcher


def extract_skills_from_text(text: str, additional_candidates: Sequence[str] | None = None) -> list[str]:
    """Extract canonical skills from free-form text.

    Combines:
    1. spaCy PhraseMatcher for exact phrase matching (e.g. 'Node.js', 'REST API', 'Machine Learning').
    2. Delimiter/bullet line parsing with RapidFuzz normalization for listed items.

    Args:
        text: Raw or section text to extract skills from.
        additional_candidates: Optional list of pre-extracted skill strings to normalize.

    Returns:
        Deduplicated list of canonical skill names preserving order.
    """
    if not text or not text.strip():
        return normalize_skills(list(additional_candidates or []))

    found_skills: list[str] = []

    # 1. spaCy PhraseMatcher
    nlp, matcher = _get_nlp_and_matcher()
    # Process text in manageable chunks if extremely long
    doc = nlp(text[:20000])
    matches = matcher(doc)
    spans = [doc[start:end] for _, start, end in matches]
    filtered = filter_spans(spans)

    for span in filtered:
        term = span.text.strip()
        if term.lower() not in _FALSE_POSITIVES:
            canonical = normalize_skill(term)
            if canonical and canonical.lower() not in _FALSE_POSITIVES:
                found_skills.append(canonical)

    # 2. Line-by-line / bullet parsing for comma/slash/bullet separated skills
    lines = text.splitlines()
    for line in lines:
        cleaned_line = line.strip()
        # Remove common bullet markers
        cleaned_line = re.sub(r"^[\s*•\-–—\d\.\)\:]+", "", cleaned_line).strip()
        if not cleaned_line:
            continue

        # If the line contains comma or slash separated terms (common in resume skill sections)
        parts = re.split(r"[,;/|•·\t]+", cleaned_line)
        for part in parts:
            item = part.strip()
            # If item is short (1 to 4 words), test if it normalizes to a known canonical skill
            words = item.split()
            if 1 <= len(words) <= 4:
                item_clean = re.sub(r"^[^a-zA-Z0-9+#.]+|[^a-zA-Z0-9+#.]+$", "", item).strip()
                if item_clean and item_clean.lower() not in _FALSE_POSITIVES:
                    norm = normalize_skill(item_clean)
                    # Only accept if it matched a known canonical alias or is already canonical
                    if norm.lower() in [c.lower() for c in SKILL_ALIASES.values()] or item_clean.lower() in SKILL_ALIASES:
                        found_skills.append(norm)

    # 3. Include any additional candidate strings
    if additional_candidates:
        for cand in additional_candidates:
            if cand and cand.strip():
                norm = normalize_skill(cand.strip())
                if norm and norm.lower() not in _FALSE_POSITIVES:
                    found_skills.append(norm)

    return normalize_skills(found_skills)
