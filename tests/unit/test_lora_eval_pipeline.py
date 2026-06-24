"""
Unit test per scripts/lora_eval_pipeline.py.
_check_hardware (subprocess mock) + _step_prep (pura trasformazione JSONL).
_step_train e _step_eval non testati: richiedono GPU + unsloth.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.lora_eval_pipeline import _check_hardware, _step_prep

_LPL = "scripts.lora_eval_pipeline"


# ── _check_hardware ───────────────────────────────────────────────────────────

def test_check_hardware_no_gpu():
    """nvidia-smi non disponibile → gpu_available=False."""
    mock_result = MagicMock(returncode=1, stdout="")
    with patch("subprocess.run", return_value=mock_result):
        hw = _check_hardware()
    assert hw["gpu_available"] is False
    assert hw["vram_gb"] == 0.0


def test_check_hardware_sufficient_vram():
    """10240 MB (10 GB) > _MIN_VRAM_GB → sufficient=True."""
    mock_result = MagicMock(returncode=0, stdout="10240\n")
    with patch("subprocess.run", return_value=mock_result):
        hw = _check_hardware()
    assert hw["gpu_available"] is True
    assert hw["vram_gb"] == pytest.approx(10.0, abs=0.1)
    assert hw["sufficient"] is True
    assert hw["note"] == ""


def test_check_hardware_insufficient_vram():
    """2048 MB (2 GB) < _MIN_VRAM_GB → sufficient=False, note non vuoto."""
    mock_result = MagicMock(returncode=0, stdout="2048\n")
    with patch("subprocess.run", return_value=mock_result):
        hw = _check_hardware()
    assert hw["sufficient"] is False
    assert "VRAM" in hw["note"] or "GB" in hw["note"]


def test_check_hardware_exception_returns_note():
    """subprocess.run solleva OSError → note non vuoto."""
    with patch("subprocess.run", side_effect=OSError("nvidia-smi not found")):
        hw = _check_hardware()
    assert hw["gpu_available"] is False
    assert "nvidia-smi" in hw["note"]


import pytest  # noqa: E402 (after the functions above that use pytest.approx)


# ── _step_prep ────────────────────────────────────────────────────────────────

def _write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records),
        encoding="utf-8",
    )


def test_step_prep_converts_jsonl_to_instruction_format(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_jsonl(corpus / "batch1.jsonl", [
        {"message": "Aurora avanzò senza fretta verso il confine della foresta.", "context": "scena 1"},
        {"message": "Corto", "context": "skip"},  # len < 20 → ignored
    ])
    out = tmp_path / "train.jsonl"
    _step_prep(corpus, out)
    lines = [json.loads(row) for row in out.read_text().splitlines() if row.strip()]
    assert len(lines) == 1
    assert lines[0]["output"] == "Aurora avanzò senza fretta verso il confine della foresta."
    assert lines[0]["input"] == "scena 1"
    assert "instruction" in lines[0]


def test_step_prep_multiple_jsonl_files(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    _write_jsonl(corpus / "a.jsonl", [{"message": "Testo lungo primo batch valido.", "context": ""}])
    _write_jsonl(corpus / "b.jsonl", [{"message": "Testo lungo secondo batch valido.", "context": ""}])
    out = tmp_path / "train.jsonl"
    _step_prep(corpus, out)
    lines = [json.loads(row) for row in out.read_text().splitlines() if row.strip()]
    assert len(lines) == 2


def test_step_prep_empty_corpus(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    out = tmp_path / "train.jsonl"
    _step_prep(corpus, out)
    assert out.exists()
    assert out.read_text().strip() == ""


def test_step_prep_skips_malformed_json(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "bad.jsonl").write_text('not-json\n{"message": "Testo valido abbastanza lungo!", "context": ""}\n', encoding="utf-8")
    out = tmp_path / "train.jsonl"
    _step_prep(corpus, out)
    lines = [row for row in out.read_text().splitlines() if row.strip()]
    assert len(lines) == 1


def test_step_prep_creates_parent_dirs(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    out = tmp_path / "subdir" / "nested" / "train.jsonl"
    _step_prep(corpus, out)
    assert out.exists()


def test_step_prep_corpus_not_found_exits(tmp_path):
    missing = tmp_path / "missing_corpus"
    out = tmp_path / "train.jsonl"
    with pytest.raises(SystemExit):
        _step_prep(missing, out)
