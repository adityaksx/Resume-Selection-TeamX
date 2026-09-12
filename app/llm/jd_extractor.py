"""JD extraction using Gemini API (plan.md §7 — LLM Job 1).

Converts raw JD text into structured JobDescription JSON.
"""

from __future__ import annotations

import logging

from app.llm.gemini_client import generate_json
from app.models.jd_models import JobDescription

logger = logging.getLogger(__name__)

JD_EXTRACTION_PROMPT = """\
You are an expert job description parser. Extract structured information from the
following Job Description text. Return a single JSON object with exactly these keys:

- "role_title": string or null — the job title
- "company": string or null — the hiring company name
- "required_skills": list of strings — skills explicitly required
- "preferred_skills": list of strings — nice-to-have or preferred skills
- "responsibilities": list of strings — key responsibilities
- "qualifications": list of strings — education or qualification requirements

Rules:
- Extract ONLY information that is explicitly stated in the text.
- Do NOT invent or assume any information.
- If a field is not mentioned, use null for strings or an empty list for lists.
- Keep skill names concise (e.g. "React", "Node.js", "MongoDB").
- Separate required skills from preferred/nice-to-have skills.
- Return ONLY the JSON object, no other text.

Job Description text:
\"\"\"
{jd_text}
\"\"\"
"""


def extract_jd(raw_text: str) -> JobDescription:
    """Extract structured JD from raw text using Gemini.

    Args:
        raw_text: Cleaned text from the JD PDF.

    Returns:
        A validated JobDescription model with raw_text preserved.

    Raises:
        ValueError: If LLM output fails Pydantic validation.
        RuntimeError: If the Gemini API call fails.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot extract JD from empty text.")

    prompt = JD_EXTRACTION_PROMPT.format(jd_text=raw_text[:8000])
    data = generate_json(prompt)

    logger.info("JD extraction returned keys: %s", list(data.keys()))

    # Validate with Pydantic
    jd = JobDescription.model_validate(data)

    # Preserve raw text for semantic matching
    jd.raw_text = raw_text

    return jd
