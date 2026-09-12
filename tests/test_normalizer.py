"""Tests for skill normalization (plan.md §8, test 5)."""

from __future__ import annotations

import pytest

from app.matching.skill_normalizer import normalize_skill, normalize_skills, SKILL_ALIASES


class TestNormalizeSkill:
    """Tests for normalize_skill()."""

    # --- Exact alias matches ---

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("ReactJS", "React"),
            ("React.js", "React"),
            ("React JS", "React"),
            ("reactjs", "React"),
            ("REACTJS", "React"),
        ],
    )
    def test_react_variants(self, raw: str, expected: str):
        """All React variants normalize to 'React' (plan.md §8)."""
        assert normalize_skill(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("NodeJS", "Node.js"),
            ("Node.js", "Node.js"),
            ("Node JS", "Node.js"),
            ("node.js", "Node.js"),
        ],
    )
    def test_nodejs_variants(self, raw: str, expected: str):
        """All Node.js variants normalize correctly."""
        assert normalize_skill(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Mongo", "MongoDB"),
            ("Mongo DB", "MongoDB"),
            ("MongoDB", "MongoDB"),
            ("mongodb", "MongoDB"),
        ],
    )
    def test_mongodb_variants(self, raw: str, expected: str):
        """All MongoDB variants normalize correctly."""
        assert normalize_skill(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("RESTful API", "REST API"),
            ("REST APIs", "REST API"),
            ("REST API development", "REST API"),
        ],
    )
    def test_rest_api_variants(self, raw: str, expected: str):
        """REST API variants normalize correctly."""
        assert normalize_skill(raw) == expected

    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("k8s", "Kubernetes"),
            ("kubernetes", "Kubernetes"),
            ("Docker", "Docker"),
            ("docker", "Docker"),
            ("git", "Git"),
            ("Git", "Git"),
        ],
    )
    def test_devops_tools(self, raw: str, expected: str):
        """DevOps tool names normalize correctly."""
        assert normalize_skill(raw) == expected

    # --- Fuzzy matching ---

    def test_fuzzy_match_close_variant(self):
        """Fuzzy matching should catch close typos/variants."""
        # "react.js" is in aliases, "reactjs" is exact — test a close fuzzy case
        result = normalize_skill("React.JS")
        assert result == "React"

    # --- Edge cases ---

    def test_unknown_skill_returned_as_is(self):
        """Skills not in the alias dictionary should be returned cleaned."""
        result = normalize_skill("Rust")
        assert result == "Rust"

    def test_empty_string(self):
        """Empty string should return empty string."""
        assert normalize_skill("") == ""

    def test_whitespace_only(self):
        """Whitespace-only string should return whitespace."""
        assert normalize_skill("   ") == "   "

    def test_whitespace_stripped(self):
        """Leading/trailing whitespace should be stripped before lookup."""
        assert normalize_skill("  React.js  ") == "React"


class TestNormalizeSkills:
    """Tests for normalize_skills()."""

    def test_deduplication(self):
        """Duplicate skills after normalization should be removed."""
        raw = ["ReactJS", "React.js", "React JS"]
        result = normalize_skills(raw)
        assert result == ["React"]

    def test_preserves_order(self):
        """Order of first-seen skills should be preserved."""
        raw = ["MongoDB", "React", "Node.js"]
        result = normalize_skills(raw)
        assert result == ["MongoDB", "React", "Node.js"]

    def test_mixed_known_and_unknown(self):
        """Mix of aliased and unknown skills should work."""
        raw = ["ReactJS", "Rust", "k8s"]
        result = normalize_skills(raw)
        assert result == ["React", "Rust", "Kubernetes"]

    def test_empty_list(self):
        """Empty list should return empty list."""
        assert normalize_skills([]) == []

    def test_plan_test5_formatting_variation(self):
        """Plan.md Test 5: NodeJS, Node.js, Node JS all normalize to one."""
        raw = ["NodeJS", "Node.js", "Node JS"]
        result = normalize_skills(raw)
        assert result == ["Node.js"]
        assert len(result) == 1
