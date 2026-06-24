"""
Unit test per scripts/seed_char_memory.py.
seed() legge YAML da CHARS_DIR, chiama upsert_char per ogni file valido.
Monkeypatching di CHARS_DIR + upsert_char per isolare dalla FS reale.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import scripts.seed_char_memory as _mod

_SEED = "scripts.seed_char_memory"


def _write_char_yaml(directory: Path, filename: str, data: dict) -> None:
    (directory / filename).write_text(
        yaml.dump(data, allow_unicode=True), encoding="utf-8"
    )


# ── seed ──────────────────────────────────────────────────────────────────────

def test_seed_returns_count(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "aurora.yaml", {"name": "Aurora", "traits": ["strega"]})
    _write_char_yaml(tmp_path, "luna.yaml", {"name": "Luna", "quirks": []})
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        n = _mod.seed()
    assert n == 2
    assert mock_upsert.call_count == 2


def test_seed_uses_yaml_name_field(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "char.yaml", {"name": "Eridani", "traits": []})
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        _mod.seed()
    called_name = mock_upsert.call_args.kwargs["name"]
    assert called_name == "Eridani"


def test_seed_falls_back_to_slug_field(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "char.yaml", {"slug": "vesper", "traits": []})
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        _mod.seed()
    called_name = mock_upsert.call_args.kwargs["name"]
    assert called_name == "vesper"


def test_seed_falls_back_to_stem(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "morgana.yaml", {"traits": []})
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        _mod.seed()
    called_name = mock_upsert.call_args.kwargs["name"]
    assert called_name == "morgana"


def test_seed_skips_non_dict_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    (tmp_path / "list.yaml").write_text("- item1\n- item2\n", encoding="utf-8")
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        n = _mod.seed()
    assert n == 0
    mock_upsert.assert_not_called()


def test_seed_skips_empty_yaml(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    (tmp_path / "empty.yaml").write_text("", encoding="utf-8")
    with patch(f"{_SEED}.upsert_char"):
        n = _mod.seed()
    assert n == 0


def test_seed_empty_dir_returns_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        n = _mod.seed()
    assert n == 0
    mock_upsert.assert_not_called()


def test_seed_passes_traits_dict_to_upsert(tmp_path, monkeypatch):
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "aurora.yaml", {
        "name": "Aurora",
        "traits": ["courageous"],
        "quirks": ["talks to sword"],
        "flaws": ["reckless"],
        "speech_pattern": {"notes": "terse"},
    })
    with patch(f"{_SEED}.upsert_char") as mock_upsert:
        _mod.seed()
    traits = mock_upsert.call_args.kwargs["traits"]
    assert traits["personality"] == ["courageous"]
    assert traits["quirks"] == ["talks to sword"]
    assert traits["speech_pattern"] == "terse"


# ── coverage gap: except branch (lines 37-38) ────────────────────────────────

def test_seed_exception_skips_file(tmp_path, monkeypatch, capsys):
    """upsert_char lancia eccezione → except branch lines 37-38: file skippato, count=0."""
    monkeypatch.setattr(_mod, "CHARS_DIR", tmp_path)
    _write_char_yaml(tmp_path, "bad.yaml", {"name": "Broken", "traits": []})
    with patch(f"{_SEED}.upsert_char", side_effect=RuntimeError("db error")):
        n = _mod.seed()
    assert n == 0
    out = capsys.readouterr().out
    assert "skip" in out
