"""LLM service layer for Phase 7 advisory and explainability features."""

from app.llm.client import (
    GeminiError,
    GeminiUnavailableError,
    generate_text,
    get_gemini_client,
    is_gemini_available,
)
from app.llm.comparison_explainer import explain_comparison_with_ai, generate_deterministic_comparison_summary
from app.llm.improvement_advisor import generate_candidate_improvement_advice, generate_deterministic_improvement_advice
from app.llm.jd_bias_detector import analyze_jd_fairness, run_deterministic_fairness_scan
from app.llm.recruiter_chat import chat_with_recruiter, resolve_candidate_references
from app.llm.top3_explainer import attach_top_ai_explanations, generate_ai_candidate_explanation

__all__ = [
    "generate_text",
    "get_gemini_client",
    "is_gemini_available",
    "GeminiError",
    "GeminiUnavailableError",
    "generate_ai_candidate_explanation",
    "attach_top_ai_explanations",
    "explain_comparison_with_ai",
    "generate_deterministic_comparison_summary",
    "generate_candidate_improvement_advice",
    "generate_deterministic_improvement_advice",
    "chat_with_recruiter",
    "resolve_candidate_references",
    "analyze_jd_fairness",
    "run_deterministic_fairness_scan",
]
