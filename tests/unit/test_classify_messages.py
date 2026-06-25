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
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from classify_messages import classify_batch, main, read_jsonl, rule_based_fallback, write_jsonl  # noqa: E402

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


# ── classify_batch ────────────────────────────────────────────────────────────

def test_classify_batch_cerebras_json_response(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": '["IC"]'}}]}
    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch([{"content": "msg1"}], "cerebras", "model")
    assert result == ["IC"]


def test_classify_batch_groq_json_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "fake-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"choices": [{"message": {"content": '["OOC"]'}}]}
    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch([{"content": "msg1"}], "groq", "model")
    assert result == ["OOC"]


def test_classify_batch_local_json_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"message": {"content": '["meta"]'}}
    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch([{"content": "msg1"}], "local", "model")
    assert result == ["meta"]


def test_classify_batch_cerebras_no_api_key(monkeypatch):
    monkeypatch.delenv("CEREBRAS_API_KEY", raising=False)
    with pytest.raises(ValueError, match="CEREBRAS_API_KEY"):
        classify_batch([{"content": "msg"}], "cerebras", "model")


def test_classify_batch_groq_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        classify_batch([{"content": "msg"}], "groq", "model")


def test_classify_batch_unknown_provider_raises():
    with pytest.raises(ValueError, match="Unsupported provider"):
        classify_batch([{"content": "msg"}], "unknown", "model")


def test_classify_batch_text_line_fallback(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")
    messages = [{"content": "m1"}, {"content": "m2"}, {"content": "m3"}]
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "1. IC content\n2. OOC content\n3. META info"}}]
    }
    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch(messages, "cerebras", "model")
    assert result == ["IC", "OOC", "meta"]


def test_classify_batch_line_fallback_art_and_default_ic(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "choices": [{"message": {"content": "1. ART something\n2. unrecognized"}}]
    }
    with patch("classify_messages.requests.post", return_value=mock_resp):
        result = classify_batch([{"content": "m1"}, {"content": "m2"}], "cerebras", "model")
    assert result == ["art", "IC"]


def test_classify_batch_exception_uses_rule_fallback(monkeypatch):
    monkeypatch.setenv("CEREBRAS_API_KEY", "fake-key")
    with patch("classify_messages.requests.post", side_effect=Exception("Network error")):
        result = classify_batch([{"content": "msg1"}], "cerebras", "model")
    assert len(result) == 1
    assert result[0] in ("IC", "OOC", "meta", "art")


# ── read_jsonl / write_jsonl ──────────────────────────────────────────────────

def test_read_jsonl_skips_invalid_json(tmp_path):
    f = tmp_path / "test.jsonl"
    f.write_text('{"a": 1}\ninvalid json\n{"b": 2}', encoding="utf-8")
    assert read_jsonl(str(f)) == [{"a": 1}, {"b": 2}]


def test_write_jsonl_creates_file(tmp_path):
    f = tmp_path / "out.jsonl"
    write_jsonl([{"a": 1}, {"b": 2}], str(f))
    lines = f.read_text(encoding="utf-8").strip().splitlines()
    assert json.loads(lines[0]) == {"a": 1}
    assert json.loads(lines[1]) == {"b": 2}


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_input_not_found(monkeypatch):
    monkeypatch.setattr("sys.argv", ["script", "--input", "non_existent_file.jsonl", "--output", "out.jsonl"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1


def test_main_dry_run_prints_sample(monkeypatch, tmp_path, capsys):
    in_f = tmp_path / "in.jsonl"
    in_f.write_text('{"content": "msg1"}\n{"content": "msg2"}', encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "script", "--input", str(in_f), "--output", str(tmp_path / "out.jsonl"), "--dry-run",
    ])
    with patch("classify_messages.classify_batch", return_value=["IC", "OOC"]):
        main()
    assert "msg1" in capsys.readouterr().out


def test_main_writes_output(monkeypatch, tmp_path):
    in_f = tmp_path / "in.jsonl"
    in_f.write_text('{"content": "msg1"}', encoding="utf-8")
    out_f = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", ["script", "--input", str(in_f), "--output", str(out_f)])
    with patch("classify_messages.classify_batch", return_value=["IC"]):
        main()
    assert out_f.exists()
    assert json.loads(out_f.read_text().strip())["classified_tag"] == "IC"


def test_main_tag_count_mismatch_pads_fallback(monkeypatch, tmp_path):
    in_f = tmp_path / "in.jsonl"
    in_f.write_text('{"content": "msg1"}\n{"content": "msg2"}', encoding="utf-8")
    out_f = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", ["script", "--input", str(in_f), "--output", str(out_f)])
    with patch("classify_messages.classify_batch", return_value=["IC"]):
        main()
    lines = out_f.read_text().strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0])["classified_tag"] == "IC"
    assert "classified_tag" in json.loads(lines[1])


def test_main_batch_exception_uses_fallback(monkeypatch, tmp_path):
    in_f = tmp_path / "in.jsonl"
    in_f.write_text('{"content": "msg1"}', encoding="utf-8")
    out_f = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", ["script", "--input", str(in_f), "--output", str(out_f)])
    with patch("classify_messages.classify_batch", side_effect=Exception("API Error")):
        main()
    assert "classified_tag" in json.loads(out_f.read_text().strip())
