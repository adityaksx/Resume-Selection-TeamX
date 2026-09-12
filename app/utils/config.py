"""Application configuration — loads environment variables."""

import os
from dataclasses import dataclass, field

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded from environment variables."""

    # Model configuration (local sentence-transformers)
    embedding_model: str = "all-MiniLM-L6-v2"

    # Scoring weights (plan.md §13)
    keyword_weight: float = 0.50
    semantic_weight: float = 0.50

    # Keyword sub-weights (plan.md §11)
    required_skill_weight: float = 0.85
    preferred_skill_weight: float = 0.15

    # Fuzzy matching threshold (plan.md §12)
    fuzzy_match_threshold: int = 85

    def validate(self) -> None:
        """Validate application settings.
        
        The engine is 100% deterministic / local ML, so no external API keys are required.
        """
        pass


def get_settings() -> Settings:
    """Return a Settings instance (factory for convenience)."""
    return Settings()
