"""Resume extraction using Gemini API (plan.md §7 — LLM Job 2).

Converts raw resume text into structured Resume JSON.
"""

from __future__ import annotations

import logging

from app.llm.gemini_client import generate_json
from app.models.resume_models import Resume

logger = logging.getLogger(__name__)

RESUME_EXTRACTION_PROMPT = """\
You are an expert resume parser. Extract structured information from the
following resume text. Return a single JSON object with exactly these keys:

- "candidate_name": string — full name of the candidate
- "contact": object with "email" (string or null) and "phone" (string or null)
- "skills": list of strings — all technical and relevant skills mentioned
- "experience": list of objects, each with:
    - "role": string or null
    - "company": string or null
    - "duration": string or null
    - "description": string or null
- "projects": list of objects, each with:
    - "name": string or null
    - "technologies": list of strings
    - "description": string or null
- "education": list of objects, each with:
    - "degree": string or null
    - "institution": string or null
    - "duration": string or null
- "certifications": list of strings

Rules:
- Extract ONLY information that is explicitly stated in the resume.
- Do NOT invent or assume any information.
- If a field is not mentioned, use null for strings or an empty list for lists.
- Include skills found in experience descriptions, project descriptions,
  and skill sections.
- Keep skill names concise (e.g. "React", "Node.js", "Python").
- Return ONLY the JSON object, no other text.

Resume text:
\"\"\"
{resume_text}
\"\"\"
"""


def extract_resume(raw_text: str) -> Resume:
    """Extract structured resume from raw text using Gemini.

    Args:
        raw_text: Cleaned text from a resume PDF.

    Returns:
        A validated Resume model with raw_text preserved.

    Raises:
        ValueError: If LLM output fails Pydantic validation.
        RuntimeError: If the Gemini API call fails.
    """
    if not raw_text or not raw_text.strip():
        raise ValueError("Cannot extract resume from empty text.")

    prompt = RESUME_EXTRACTION_PROMPT.format(resume_text=raw_text[:8000])
    data = generate_json(prompt)

    logger.info("Resume extraction returned keys: %s", list(data.keys()))

    # Validate with Pydantic
    resume = Resume.model_validate(data)

    # Preserve raw text for semantic matching
    resume.raw_text = raw_text

    return resume
