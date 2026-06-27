"""GAP-47: test per circuit-breaker, write_profiles, resolve_write_model, parse helpers."""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.scene_refine import (
    _BREAKER_THRESHOLD,
    _breaker_fail,
    _breaker_ok,
    _breaker_open,
    _is_quota_error,
    _parse_retry_after,
    active_write_profile,
    reset_circuit_breakers,
    resolve_write_model,
    set_write_profile,
    write_profiles,
)


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    """Ripristina breaker e profilo dopo ogni test."""
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()
    # ripristina profilo cloud
    try:
        set_write_profile("cloud")
    except Exception:
        pass


# ── write_profiles ────────────────────────────────────────────────────────────


def test_write_profiles_has_cloud_and_local():
    profiles = write_profiles()
    assert "cloud" in profiles
    assert "local" in profiles


def test_write_profiles_cloud_tuple(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_PROVIDER", raising=False)
    monkeypatch.delenv("CALLIOPE_WRITE_MODEL", raising=False)
    provider, model = write_profiles()["cloud"]
    assert isinstance(provider, str) and provider
    assert isinstance(model, str) and model


def test_write_profiles_env_override(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "groq")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "llama3-test")
    provider, model = write_profiles()["cloud"]
    assert provider == "groq"
    assert model == "llama3-test"


def test_write_profiles_local_env_override(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_LOCAL_PROVIDER", "ollama_test")
    monkeypatch.setenv("CALLIOPE_WRITE_LOCAL_MODEL", "phi3")
    provider, model = write_profiles()["local"]
    assert provider == "ollama_test"
    assert model == "phi3"


# ── active_write_profile / set_write_profile ──────────────────────────────────


def test_active_write_profile_default_cloud():
    assert active_write_profile() == "cloud"


def test_set_write_profile_local():
    set_write_profile("local")
    assert active_write_profile() == "local"


def test_set_write_profile_back_to_cloud():
    set_write_profile("local")
    set_write_profile("cloud")
    assert active_write_profile() == "cloud"


def test_set_write_profile_invalid_raises():
    with pytest.raises(ValueError):
        set_write_profile("unknown_profile")


# ── resolve_write_model ───────────────────────────────────────────────────────


def test_resolve_write_model_returns_tuple():
    result = resolve_write_model()
    assert isinstance(result, tuple)
    assert len(result) == 2


def test_resolve_write_model_cloud_default():
    provider, model = resolve_write_model()
    # deve matchare write_profiles()["cloud"]
    assert (provider, model) == write_profiles()["cloud"]


def test_resolve_write_model_local_after_switch():
    set_write_profile("local")
    provider, model = resolve_write_model()
    assert (provider, model) == write_profiles()["local"]


# ── circuit breaker ───────────────────────────────────────────────────────────


def test_breaker_closed_initially():
    assert _breaker_open("cerebras") is False


def test_breaker_opens_after_threshold_fails():
    for _ in range(_BREAKER_THRESHOLD):
        _breaker_fail("cerebras")
    assert _breaker_open("cerebras") is True


def test_breaker_ok_resets():
    for _ in range(_BREAKER_THRESHOLD):
        _breaker_fail("cerebras")
    _breaker_ok("cerebras")
    assert _breaker_open("cerebras") is False


def test_breaker_below_threshold_still_closed():
    for _ in range(_BREAKER_THRESHOLD - 1):
        _breaker_fail("cerebras")
    assert _breaker_open("cerebras") is False


def test_reset_circuit_breakers_clears_all():
    _breaker_fail("cerebras")
    _breaker_fail("groq")
    reset_circuit_breakers()
    assert _breaker_open("cerebras") is False
    assert _breaker_open("groq") is False


def test_breaker_independent_providers():
    for _ in range(_BREAKER_THRESHOLD):
        _breaker_fail("cerebras")
    assert _breaker_open("cerebras") is True
    assert _breaker_open("groq") is False


# ── _parse_retry_after ────────────────────────────────────────────────────────


def _mock_resp(header_val=None):
    headers = {}
    if header_val is not None:
        headers["Retry-After"] = header_val
    return SimpleNamespace(headers=headers)


def test_parse_retry_after_none_when_missing():
    assert _parse_retry_after(_mock_resp()) is None


def test_parse_retry_after_numeric():
    assert _parse_retry_after(_mock_resp("30")) == 30.0


def test_parse_retry_after_float():
    assert _parse_retry_after(_mock_resp("1.5")) == 1.5


def test_parse_retry_after_zero_clamped():
    assert _parse_retry_after(_mock_resp("-5")) == 0.0


def test_parse_retry_after_invalid_string_returns_none():
    assert _parse_retry_after(_mock_resp("tomorrow")) is None


# ── _is_quota_error ───────────────────────────────────────────────────────────


def test_is_quota_error_daily_quota():
    assert _is_quota_error(429, "daily_quota_exceeded") is True


def test_is_quota_error_throughput_not_quota():
    assert _is_quota_error(429, "rate_limit_exceeded") is False


def test_is_quota_error_tokens_per_day():
    assert _is_quota_error(429, "tokens_per_day_exceeded") is True


def test_is_quota_error_insufficient():
    assert _is_quota_error(429, "insufficient_quota") is True


def test_is_quota_error_non_429():
    assert _is_quota_error(503, "quota_exceeded") is False


def test_is_quota_error_empty_code():
    assert _is_quota_error(429, "") is False
