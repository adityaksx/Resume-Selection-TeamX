"""Server-side Gemini LLM Client (plan.md Phase 7B).

Provides a secure, isolated client for generative advisory features (top-3 explanations,
recruiter chat, comparison, candidate improvement, and JD fairness analysis).
The API key is strictly server-side and never exposed to clients, browser requests, or logs.
If the API key is missing or invalid, functions degrade gracefully without impacting core ranking.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from google import genai
from google.genai import types

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

DEFAULT_GEMINI_MODEL = "gemini-2.5-flash"


class GeminiError(Exception):
    """Base exception for Gemini LLM operations."""


class GeminiUnavailableError(GeminiError):
    """Raised when GEMINI_API_KEY is absent or client cannot be initialized."""


def get_api_key() -> str:
    """Retrieve Gemini API key from settings or environment.
    
    Never logs or exposes the key value.
    """
    key = get_settings().gemini_api_key or os.getenv("GEMINI_API_KEY", "")
    return key.strip()


def is_gemini_available() -> bool:
    """Check whether Gemini API key is configured."""
    return bool(get_api_key())


_client_instance: genai.Client | None = None
_cached_key: str = ""


def get_gemini_client() -> genai.Client:
    """Initialize or return cached genai.Client instance.

    Raises:
        GeminiUnavailableError: If GEMINI_API_KEY is not configured.
    """
    global _client_instance, _cached_key

    api_key = get_api_key()
    if not api_key:
        raise GeminiUnavailableError(
            "GEMINI_API_KEY is not configured. Set GEMINI_API_KEY in your environment or .env file."
        )

    if _client_instance is None or _cached_key != api_key:
        _client_instance = genai.Client(api_key=api_key)
        _cached_key = api_key
        logger.info("Initialized Gemini client with model: %s", DEFAULT_GEMINI_MODEL)

    return _client_instance


def generate_text(
    prompt: str,
    system_instruction: str | None = None,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.2,
) -> str:
    """Generate text completion from Gemini.

    Args:
        prompt: Prompt content for the model.
        system_instruction: Optional system instruction / role guidance.
        model: Model name (defaults to gemini-2.5-flash).
        temperature: Sampling temperature (lower for deterministic grounded output).

    Returns:
        Generated text string.

    Raises:
        GeminiUnavailableError: If API key is missing.
        GeminiError: If generation fails.
    """
    client = get_gemini_client()

    config = types.GenerateContentConfig(
        temperature=temperature,
        system_instruction=system_instruction if system_instruction else None,
    )

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config=config,
        )
        if not response or not response.text:
            raise GeminiError("Gemini returned an empty response.")
        return response.text.strip()
    except GeminiError:
        raise
    except Exception as exc:
        logger.error("Gemini text generation failed: %s", exc)
        raise GeminiError(f"Gemini API request failed: {exc}") from exc
