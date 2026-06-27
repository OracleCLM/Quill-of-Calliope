"""GAP-69: test per _memory_blocks e _call_gateway in write_routes.py."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import app.calliope_shell.write_routes as wr
from flask import Flask

# Flask app context per jsonify
_app = Flask(__name__)


# ═══════════════════════════════════════════════════════════════════
# _memory_blocks
# ═══════════════════════════════════════════════════════════════════


def test_memory_blocks_empty_names_returns_empty():
    result = wr._memory_blocks([], "query")
    assert result == []


def test_memory_blocks_retrieve_raises_returns_empty():
    with patch("app.calliope_shell.char_memory.retrieve_multi_signal", side_effect=RuntimeError("fail")):
        result = wr._memory_blocks(["Aurora"], "test query")
    assert result == []


def test_memory_blocks_returns_formatted_strings():
    hits = [{"fact_text": "è coraggiosa"}, {"fact_text": "parla poco"}]
    with patch("app.calliope_shell.char_memory.retrieve_multi_signal", return_value=hits):
        result = wr._memory_blocks(["Aurora"], "query")
    assert any("Aurora: è coraggiosa" in r for r in result)


def test_memory_blocks_max_two_per_char():
    hits = [{"fact_text": f"fatto{i}"} for i in range(5)]
    with patch("app.calliope_shell.char_memory.retrieve_multi_signal", return_value=hits):
        result = wr._memory_blocks(["Mao"], "q")
    assert len(result) <= 2


def test_memory_blocks_max_three_chars():
    hits = [{"fact_text": "x"}]
    with patch("app.calliope_shell.char_memory.retrieve_multi_signal", return_value=hits):
        result = wr._memory_blocks(["A", "B", "C", "D"], "q")
    assert len(result) <= 3 * 2  # max 3 chars × max 2 hits


def test_memory_blocks_skips_empty_name():
    hits = [{"fact_text": "ok"}]
    with patch("app.calliope_shell.char_memory.retrieve_multi_signal", return_value=hits) as mock_fn:
        wr._memory_blocks(["", "Aurora"], "q")
    mock_fn.assert_called_once()  # "" saltato, solo Aurora


# ═══════════════════════════════════════════════════════════════════
# _call_gateway
# ═══════════════════════════════════════════════════════════════════


def test_call_gateway_connection_error_returns_503():
    import requests as _req
    with _app.app_context():
        with patch("requests.post", side_effect=_req.exceptions.ConnectionError):
            text, err = wr._call_gateway("llm_code", {"prompt": "x"})
    assert text == ""
    assert err is not None
    resp, status = err
    assert status == 503


def test_call_gateway_generic_exception_returns_503():
    with _app.app_context():
        with patch("requests.post", side_effect=RuntimeError("boom")):
            text, err = wr._call_gateway("llm_code", {"prompt": "x"})
    assert text == ""
    assert err is not None
    _, status = err
    assert status == 503


def test_call_gateway_success_returns_text():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"result": "Testo generato."}
    with _app.app_context():
        with patch("requests.post", return_value=mock_resp):
            text, err = wr._call_gateway("llm_code", {"prompt": "x"})
    assert text == "Testo generato."
    assert err is None


def test_call_gateway_success_no_error():
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {"text": "Risposta gateway."}
    with _app.app_context():
        with patch("requests.post", return_value=mock_resp):
            _, err = wr._call_gateway("llm_code", {"prompt": "x"})
    assert err is None
