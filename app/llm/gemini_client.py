"""Gemini API client wrapper.

Handles API key loading, model initialization, and structured JSON generation.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

import google.generativeai as genai

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

# Module-level cache to avoid re-initializing on every call
_configured = False


def _ensure_configured() -> None:
    """Configure the Gemini SDK with the API key (once)."""
    global _configured
    if not _configured:
        settings = get_settings()
        settings.validate()
        genai.configure(api_key=settings.gemini_api_key)
        _configured = True


def get_gemini_model() -> genai.GenerativeModel:
    """Initialize and return a Gemini GenerativeModel instance."""
    _ensure_configured()
    settings = get_settings()
    return genai.GenerativeModel(settings.gemini_model)


def _extract_json_from_response(text: str) -> str:
    """Extract JSON from a response that may contain markdown code fences.

    Args:
        text: Raw LLM response text.

    Returns:
        Clean JSON string.
    """
    # Strip markdown code fences if present
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()


def generate_json(prompt: str, max_retries: int = 2) -> dict[str, Any]:
    """Send a prompt to Gemini and parse the response as JSON.

    Implements plan.md §19 retry logic:
        1. First attempt with the given prompt.
        2. On JSON parse failure, retry with a stricter prompt.

    Args:
        prompt: The full prompt expecting a JSON response.
        max_retries: Maximum number of retry attempts.

    Returns:
        Parsed JSON as a Python dict.

    Raises:
        ValueError: If the LLM response cannot be parsed as valid JSON
                    after all retries.
        RuntimeError: If the Gemini API call fails.
    """
    model = get_gemini_model()
    last_error: Exception | None = None

    for attempt in range(max_retries):
        try:
            if attempt == 0:
                current_prompt = prompt
            else:
                # Stricter retry prompt (plan.md §19)
                current_prompt = (
                    f"{prompt}\n\n"
                    "CRITICAL: Your previous response was not valid JSON. "
                    "Return ONLY a single valid JSON object. "
                    "No markdown, no explanation, no text outside the JSON."
                )

            response = model.generate_content(current_prompt)
            raw_text = response.text
            json_str = _extract_json_from_response(raw_text)
            return json.loads(json_str)

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                "Attempt %d: Failed to parse JSON from Gemini response: %s",
                attempt + 1,
                e,
            )
        except Exception as e:
            raise RuntimeError(f"Gemini API call failed: {e}") from e

    raise ValueError(
        f"Failed to get valid JSON from Gemini after {max_retries} attempts. "
        f"Last error: {last_error}"
    )
