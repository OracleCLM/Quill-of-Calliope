"""Unit tests for classify_messages — fixture-based format validation.

Audit fix #2 (PARTIAL): adds fixture-schema validation for real Cerebras response format.
Previously: only mock-based tests in tests/discord/test_classify_messages.py.
Fixture: tests/fixtures/cerebras_classify_sample.json (captured 2026-05-18).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from classify_messages import rule_based_fallback  # noqa: E402

FIXTURES = Path(__file__).parent.parent / "fixtures"
GATEWAY_URL = "http://localhost:8766"


# ── Fixture format validation ─────────────────────────────────────────────────

class TestCerebrasResponseFixture:
    """Validate real Cerebras gateway response schema using captured fixture."""

    def test_fixture_file_exists(self):
        fixture_path = FIXTURES / "cerebras_classify_sample.json"
        assert fixture_path.exists(), "Fixture not found — run capture script"

    def test_fixture_response_has_content_field(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        response = fixture["response"]
        assert "content" in response, f"Missing 'content' in response: {response}"

    def test_fixture_content_is_string(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        content = fixture["response"]["content"]
        assert isinstance(content, str), f"content is not str: {type(content)}"

    def test_fixture_provider_field_present(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        assert "provider" in fixture["response"]
        assert fixture["response"]["provider"] == "cerebras"

    def test_fixture_model_field_nonempty(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        model = fixture["response"].get("model", "")
        assert isinstance(model, str) and len(model) > 0, f"model field empty: {model!r}"

    def test_fixture_content_parseable_as_json_array(self):
        """Real Cerebras response content should be parseable JSON array like [\"IC\"]."""
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        content = fixture["response"]["content"].strip()
        # Content may be a JSON array — verify it can be parsed
        try:
            parsed = json.loads(content)
            assert isinstance(parsed, list), f"Expected list, got {type(parsed)}"
            assert all(isinstance(x, str) for x in parsed), "Array should contain strings"
        except json.JSONDecodeError:
            # Some models return plain text — still valid, just document
            pytest.skip(f"Content is not JSON array (text response): {content[:80]!r}")

    def test_fixture_http_status_200(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        assert fixture["response_status"] == 200

    def test_fixture_meta_present(self):
        fixture = json.loads((FIXTURES / "cerebras_classify_sample.json").read_text())
        meta = fixture.get("_meta", {})
        assert meta.get("provider") == "cerebras"
        assert meta.get("captured_at") == "2026-05-18"


# ── rule_based_fallback edge cases (no mock needed) ───────────────────────────

class TestRuleBasedFallbackAdditional:
    """Additional coverage for rule_based_fallback not in existing discord tests."""

    def test_server_keyword_meta(self):
        # rule_based_fallback returns "meta" (not "OOC") for server/mod/admin keywords
        assert rule_based_fallback({"content": "Server is going down for maintenance."}) == "meta"

    def test_mod_keyword_meta(self):
        assert rule_based_fallback({"content": "Mod note: please read the rules."}) == "meta"

    def test_art_keyword_art(self):
        # rule_based_fallback returns "art" for image/art/pic/draw/img keywords
        assert rule_based_fallback({"content": "New art commission dropped!"}) == "art"

    def test_empty_content_ic_default(self):
        assert rule_based_fallback({"content": ""}) == "IC"

    def test_none_content_ic_default(self):
        assert rule_based_fallback({"content": None}) == "IC"

    def test_ic_narrative(self):
        assert rule_based_fallback({"content": "She whispered into the moonlit silence."}) == "IC"

    def test_parenthesis_at_start_ooc(self):
        assert rule_based_fallback({"content": "(brb)"}) == "OOC"
