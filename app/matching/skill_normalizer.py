"""Skill normalization — alias dictionary + fuzzy matching (plan.md §8).

Canonicalizes skill names so "ReactJS", "React.js", "React JS" all map to "React".
"""

from __future__ import annotations

import logging

from rapidfuzz import fuzz, process

from app.utils.config import get_settings

logger = logging.getLogger(__name__)

# Canonical alias dictionary (plan.md §8)
SKILL_ALIASES: dict[str, str] = {
    "reactjs": "React",
    "react.js": "React",
    "react js": "React",
    "nodejs": "Node.js",
    "node js": "Node.js",
    "node.js": "Node.js",
    "mongo": "MongoDB",
    "mongo db": "MongoDB",
    "mongodb": "MongoDB",
    "restful api": "REST API",
    "rest apis": "REST API",
    "rest api development": "REST API",
    "expressjs": "Express",
    "express.js": "Express",
    "express js": "Express",
    "typescript": "TypeScript",
    "type script": "TypeScript",
    "javascript": "JavaScript",
    "java script": "JavaScript",
    "js": "JavaScript",
    "java": "Java",
    "python": "Python",
    "python3": "Python",
    "python 3": "Python",
    "html": "HTML",
    "html5": "HTML",
    "css": "CSS",
    "css3": "CSS",
    "amazon web services": "AWS",
    "google cloud platform": "GCP",
    "gcp": "GCP",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "c": "C",
    "c++": "C++",
    "cplusplus": "C++",
    "c plus plus": "C++",
    "c#": "C#",
    "csharp": "C#",
    "c sharp": "C#",
    "rust": "Rust",
    "go": "Go",
    "golang": "Go",
    "postgresql": "PostgreSQL",
    "postgres": "PostgreSQL",
    "mysql": "MySQL",
    "my sql": "MySQL",
    "docker": "Docker",
    "kubernetes": "Kubernetes",
    "k8s": "Kubernetes",
    "git": "Git",
    "github": "GitHub",
    "tailwindcss": "Tailwind CSS",
    "tailwind css": "Tailwind CSS",
    "tailwind": "Tailwind CSS",
    "next.js": "Next.js",
    "nextjs": "Next.js",
    "next js": "Next.js",
    "vue.js": "Vue.js",
    "vuejs": "Vue.js",
    "vue js": "Vue.js",
    "angular.js": "Angular",
    "angularjs": "Angular",
    "machine learning": "Machine Learning",
    "ml": "Machine Learning",
    "deep learning": "Deep Learning",
    "dl": "Deep Learning",
    "natural language processing": "NLP",
    "nlp": "NLP",
    "tensorflow": "TensorFlow",
    "tf": "TensorFlow",
    "pytorch": "PyTorch",
    "flask": "Flask",
    "django": "Django",
    "spring boot": "Spring Boot",
    "springboot": "Spring Boot",
    "sql": "SQL",
    "nosql": "NoSQL",
    "graphql": "GraphQL",
    "redis": "Redis",
    "firebase": "Firebase",
    "figma": "Figma",
    "linux": "Linux",
}

# Pre-compute the set of canonical names for fuzzy matching targets
_CANONICAL_NAMES: list[str] = sorted(set(SKILL_ALIASES.values()))


def normalize_skill(skill: str) -> str:
    """Normalize a single skill name to its canonical form.

    Strategy:
        1. Exact match in alias dictionary (case-insensitive).
        2. Fuzzy match against alias keys above the configured threshold.
        3. If no match, return the original skill stripped/title-cased.

    Args:
        skill: Raw skill string.

    Returns:
        Canonical skill name.
    """
    if not skill or not skill.strip():
        return skill

    cleaned = skill.strip()
    key = cleaned.lower()

    # 1. Exact alias lookup
    if key in SKILL_ALIASES:
        return SKILL_ALIASES[key]

    # 2. Fuzzy match against alias keys
    settings = get_settings()
    threshold = settings.fuzzy_match_threshold

    alias_keys = list(SKILL_ALIASES.keys())
    result = process.extractOne(
        key,
        alias_keys,
        scorer=fuzz.ratio,
        score_cutoff=threshold,
    )
    if result is not None:
        matched_key, score, _ = result
        canonical = SKILL_ALIASES[matched_key]
        logger.debug(
            "Fuzzy matched '%s' → '%s' (via alias '%s', score=%d)",
            skill, canonical, matched_key, score,
        )
        return canonical

    # 3. No match — return cleaned original
    return cleaned


def normalize_skills(skills: list[str]) -> list[str]:
    """Normalize a list of skills, preserving order and removing duplicates.

    Args:
        skills: List of raw skill strings.

    Returns:
        List of canonical skill names (deduplicated, order-preserving).
    """
    seen: set[str] = set()
    result: list[str] = []
    for skill in skills:
        normalized = normalize_skill(skill)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
