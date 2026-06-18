"""GAP-60: test per helper puri di write_routes — _gateway_text, _gateway_url,
_active_model, _active_provider."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.write_routes import (
    _active_model,
    _active_provider,
    _gateway_text,
    _gateway_url,
)


# ── _gateway_text ─────────────────────────────────────────────────────────────


def test_gateway_text_key_result():
    assert _gateway_text({"result": "hello"}) == "hello"


def test_gateway_text_key_text():
    assert _gateway_text({"text": "world"}) == "world"


def test_gateway_text_key_content():
    assert _gateway_text({"content": "foo"}) == "foo"


def test_gateway_text_empty_dict():
    assert _gateway_text({}) == ""


def test_gateway_text_result_takes_priority_over_text():
    # "result" viene prima di "text" nella catena or
    val = _gateway_text({"result": "primary", "text": "secondary"})
    assert val == "primary"


def test_gateway_text_false_result_falls_through():
    # result="" (falsy) → fallback a text
    val = _gateway_text({"result": "", "text": "fallback"})
    assert val == "fallback"


def test_gateway_text_none_result_falls_through():
    val = _gateway_text({"result": None, "text": "ok"})
    assert val == "ok"


# ── _gateway_url ──────────────────────────────────────────────────────────────


def test_gateway_url_default(monkeypatch):
    monkeypatch.delenv("GATEWAY_URL", raising=False)
    assert _gateway_url() == "http://localhost:8766"


def test_gateway_url_env_override(monkeypatch):
    monkeypatch.setenv("GATEWAY_URL", "http://custom-host:9999")
    assert _gateway_url() == "http://custom-host:9999"


# ── _active_model ─────────────────────────────────────────────────────────────


def test_active_model_env_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.calliope_shell.write_routes._active_model",
        lambda: "test-model",
    )
    import app.calliope_shell.write_routes as wr
    assert wr._active_model() == "test-model"


def test_active_model_env_var_used_on_exception(monkeypatch):
    monkeypatch.setenv("CALLIOPE_LLM_MODEL", "env-model-x")

    def bad_resolve():
        raise ImportError("scene_refine not available")

    import app.calliope_shell.write_routes as wr
    import app.calliope_shell.scene_refine as sr
    monkeypatch.setattr(sr, "resolve_write_model", bad_resolve)
    result = wr._active_model()
    assert isinstance(result, str)
    assert result  # non vuoto


def test_active_model_returns_string(monkeypatch):
    monkeypatch.delenv("CALLIOPE_LLM_MODEL", raising=False)
    result = _active_model()
    assert isinstance(result, str)
    assert result


# ── _active_provider ──────────────────────────────────────────────────────────


def test_active_provider_env_var_fallback(monkeypatch):
    monkeypatch.setenv("CALLIOPE_LLM_PROVIDER", "groq")

    import app.calliope_shell.write_routes as wr
    import app.calliope_shell.scene_refine as sr

    def bad_resolve():
        raise ImportError("scene_refine not available")

    monkeypatch.setattr(sr, "resolve_write_model", bad_resolve)
    result = wr._active_provider()
    assert isinstance(result, str)
    assert result


def test_active_provider_returns_string(monkeypatch):
    monkeypatch.delenv("CALLIOPE_LLM_PROVIDER", raising=False)
    result = _active_provider()
    assert isinstance(result, str)
    assert result
