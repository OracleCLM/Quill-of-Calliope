"""GAP-72: test per write_model_chain in scene_refine.py — env driven, dedup, parsing."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_refine import write_model_chain


def test_chain_returns_list(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_FALLBACKS", raising=False)
    result = write_model_chain()
    assert isinstance(result, list)
    assert len(result) >= 1


def test_chain_first_element_is_tuple_of_strings(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_FALLBACKS", raising=False)
    result = write_model_chain()
    primary = result[0]
    assert isinstance(primary, tuple)
    assert len(primary) == 2
    assert isinstance(primary[0], str) and isinstance(primary[1], str)


def test_chain_custom_fallbacks(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:llama-3.3-70b-versatile,openrouter:qwen3-coder")
    result = write_model_chain()
    providers = [p for p, _ in result]
    assert "groq" in providers
    assert "openrouter" in providers


def test_chain_no_duplicates(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "groq")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:llama-3.3-70b-versatile,cerebras:zai-glm-4.7")
    result = write_model_chain()
    assert result.count(("groq", "llama-3.3-70b-versatile")) == 1


def test_chain_skips_item_without_colon(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "bad-item,groq:llama-3.3-70b-versatile")
    result = write_model_chain()
    providers = [p for p, _ in result]
    assert "bad-item" not in providers
    assert "groq" in providers


def test_chain_skips_empty_items(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", ",groq:llama-3.3-70b-versatile,,")
    result = write_model_chain()
    pairs = [(p, m) for p, m in result if p and m]
    assert len(pairs) == len(result)


def test_chain_empty_fallbacks_returns_only_primary(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "")
    result = write_model_chain()
    assert len(result) == 1
