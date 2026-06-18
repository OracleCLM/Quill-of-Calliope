"""GAP-56: test per write_model_chain — composizione chain provider/model."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest

from app.calliope_shell.scene_refine import (
    reset_circuit_breakers,
    resolve_write_model,
    set_write_profile,
    write_model_chain,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()
    try:
        set_write_profile("cloud")
    except Exception:
        pass


# ── struttura chain ───────────────────────────────────────────────────────────


def test_chain_is_list():
    assert isinstance(write_model_chain(), list)


def test_chain_not_empty():
    assert len(write_model_chain()) >= 1


def test_chain_first_element_is_primary():
    primary = resolve_write_model()
    assert write_model_chain()[0] == primary


def test_chain_each_item_is_tuple_of_two_strings():
    for item in write_model_chain():
        assert isinstance(item, tuple)
        assert len(item) == 2
        assert all(isinstance(s, str) and s for s in item)


def test_chain_default_has_multiple_entries(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_FALLBACKS", raising=False)
    assert len(write_model_chain()) > 1


# ── env CALLIOPE_WRITE_FALLBACKS ──────────────────────────────────────────────


def test_chain_custom_fallback(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:llama-test")
    chain = write_model_chain()
    assert any(p == "groq" and m == "llama-test" for p, m in chain)


def test_chain_multiple_fallbacks(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:m1,openrouter:m2")
    chain = write_model_chain()
    names = [p for p, _ in chain]
    assert "groq" in names
    assert "openrouter" in names


def test_chain_skips_empty_entries(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:m1,,openrouter:m2")
    chain = write_model_chain()
    for p, m in chain:
        assert p and m


def test_chain_skips_no_colon_entries(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "invalidsanscolon,groq:llama-ok")
    chain = write_model_chain()
    providers = [p for p, _ in chain]
    assert "invalidsanscolon" not in providers


def test_chain_no_duplicates(monkeypatch):
    # Imposta fallback = stesso valore del primary → non deve essere duplicato
    primary = resolve_write_model()
    fb = f"{primary[0]}:{primary[1]}"
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", fb)
    chain = write_model_chain()
    assert chain.count(primary) == 1


def test_chain_empty_fallbacks_env_gives_only_primary(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "")
    chain = write_model_chain()
    assert len(chain) == 1
    assert chain[0] == resolve_write_model()
