"""Application configuration — loads environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))

    # Model configuration
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "all-MiniLM-L6-v2"

    # Scoring weights (plan.md §11)
    keyword_weight: float = 0.50
    semantic_weight: float = 0.50

    # Keyword sub-weights (plan.md §9)
    required_skill_weight: float = 0.85
    preferred_skill_weight: float = 0.15

    # Fuzzy matching threshold (plan.md §8)
    fuzzy_match_threshold: int = 85

    def validate(self) -> None:
        """Raise ValueError if critical settings are missing."""
        if not self.gemini_api_key:
            raise ValueError(
                "GEMINI_API_KEY is not set. "
                "Copy .env.example to .env and add your key."
            )


def get_settings() -> Settings:
    """Return a Settings instance (factory for convenience)."""
    return Settings()
