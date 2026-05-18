"""Tests for dispatch_to_tier() and helpers in scripts/route_scene.py."""

import json
import sys
import unittest
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(__import__("pathlib").Path(__file__).parents[2] / "scripts"))
from route_scene import DEFAULT_CONFIG, dispatch_to_tier  # noqa: E402


def _make_response(body: dict) -> MagicMock:
    """Return a mock context-manager that simulates urlopen response."""
    raw = json.dumps(body).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


class TestGatewayCerebrasSuccess(unittest.TestCase):
    """Scenario 1 — happy-path cerebras call returns content."""

    def test_gateway_cerebras_success(self):
        mock_resp = _make_response({"content": "scene text", "provider": "cerebras", "model": "qwen-3-235b-a22b"})
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_open:
            result = dispatch_to_tier(
                "cerebras_workhorse",
                "Write a battle scene",
                config=DEFAULT_CONFIG,
                timeout=5,
                max_retries=3,
            )
        self.assertEqual(result, "scene text")
        mock_open.assert_called_once()


class TestGatewayRetryThenSuccess(unittest.TestCase):
    """Scenario 2 — first attempt raises, second returns OK."""

    def test_gateway_retry_then_success(self):
        ok_resp = _make_response({"content": "ok scene", "provider": "cerebras", "model": "qwen-3-235b-a22b"})
        side_effects = [Exception("connection refused"), ok_resp]

        with patch("urllib.request.urlopen", side_effect=side_effects) as mock_open, \
             patch("time.sleep"):  # avoid real sleep
            result = dispatch_to_tier(
                "cerebras_workhorse",
                "Retry me",
                config=DEFAULT_CONFIG,
                timeout=5,
                max_retries=3,
            )
        self.assertEqual(result, "ok scene")
        self.assertEqual(mock_open.call_count, 2)


class TestOllamaFallbackModel(unittest.TestCase):
    """Scenario 3 — primary ollama model fails, qwen2.5:7b-instruct succeeds."""

    def test_ollama_fallback_model(self):
        fail_resp = MagicMock()
        fail_resp.__enter__ = lambda s: s
        fail_resp.__exit__ = MagicMock(return_value=False)
        fail_resp.read.side_effect = Exception("model not found")

        ok_resp = _make_response({"response": "local scene"})

        call_count = {"n": 0}

        def urlopen_side(req, timeout=None):
            call_count["n"] += 1
            body = json.loads(req.data)
            if body["model"] == "dolphin-mistral-24b":
                raise Exception("model not found")
            return ok_resp

        with patch("urllib.request.urlopen", side_effect=urlopen_side):
            result = dispatch_to_tier(
                "ollama_uncensored",
                "Generate NSFW scene",
                config=DEFAULT_CONFIG,
                timeout=5,
            )
        self.assertEqual(result, "local scene")
        # primary model tried (and failed) + fallback tried
        self.assertGreaterEqual(call_count["n"], 2)


class TestClaudeSubprocessSuccess(unittest.TestCase):
    """Scenario 4 — claude subprocess returns returncode=0 and stdout='scene'."""

    def test_claude_subprocess_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "scene\n"
        mock_result.stderr = ""

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = dispatch_to_tier(
                "claude_subprocess",
                "Write a climax scene",
                config=DEFAULT_CONFIG,
                timeout=10,
            )
        self.assertEqual(result, "scene")
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        self.assertIn("claude", args[0])
        self.assertEqual(kwargs["input"], "Write a climax scene")


class TestUnknownProviderRaises(unittest.TestCase):
    """Scenario 5 — tier with provider='unknown' raises ValueError."""

    def test_unknown_provider_raises(self):
        custom_config = {
            "matrix": {
                "default": {"tier": "custom_tier", "provider": "unknown", "model": "x"},
            },
            "nsfw_threshold": 2,
            "block_thresholds": {"non_consent": 3, "minors_adjacent": 3},
        }
        with self.assertRaises(ValueError) as ctx:
            dispatch_to_tier("custom_tier", "test prompt", config=custom_config)
        self.assertIn("Unknown provider", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
