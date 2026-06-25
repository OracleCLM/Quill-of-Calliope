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

import pytest

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


def test_step_prep_skips_blank_lines(tmp_path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "a.jsonl").write_text(
        '\n{"message": "Testo abbastanza lungo per passare il filtro!", "context": ""}\n\n',
        encoding="utf-8",
    )
    out = tmp_path / "train.jsonl"
    _step_prep(corpus, out)
    lines = [row for row in out.read_text().splitlines() if row.strip()]
    assert len(lines) == 1


# ─────────────────────────────────────────────────────────────────────────────
# Extended tests — _step_train (hardware paths), _step_eval, main()
# ─────────────────────────────────────────────────────────────────────────────

from scripts.lora_eval_pipeline import _step_train, _step_eval, main  # noqa: E402

_LPL = "scripts.lora_eval_pipeline"


# ── _step_train ───────────────────────────────────────────────────────────────

def test_step_train_insufficient_hardware_exits(tmp_path):
    insufficient = {"gpu_available": True, "vram_gb": 2.0, "sufficient": False,
                    "note": "VRAM 2.0GB < 8GB required"}
    with patch(f"{_LPL}._check_hardware", return_value=insufficient):
        with pytest.raises(SystemExit) as exc:
            _step_train(tmp_path / "train.jsonl", tmp_path / "adapter")
    assert exc.value.code == 3


def test_step_train_unsloth_not_installed_exits(tmp_path):
    sufficient = {"gpu_available": True, "vram_gb": 10.0, "sufficient": True, "note": ""}
    with patch(f"{_LPL}._check_hardware", return_value=sufficient):
        with patch.dict(sys.modules, {"unsloth": None}):
            with pytest.raises(SystemExit) as exc:
                _step_train(tmp_path / "train.jsonl", tmp_path / "adapter")
    assert exc.value.code == 2


# ── _step_eval ────────────────────────────────────────────────────────────────

def test_step_eval_writes_report(tmp_path):
    mock_report = MagicMock(cliche_count=2, style_drift_score=0.3)
    mock_style_coach = MagicMock()
    mock_style_coach.lint_scene_output = MagicMock(return_value=mock_report)
    mock_app_shell = MagicMock()
    mock_app_shell.style_coach = mock_style_coach
    mock_app = MagicMock()
    mock_app.calliope_shell = mock_app_shell
    with patch.dict(sys.modules, {
        "app": mock_app,
        "app.calliope_shell": mock_app_shell,
        "app.calliope_shell.style_coach": mock_style_coach,
    }):
        report_path = tmp_path / "report.md"
        _step_eval(tmp_path / "adapter", report_path)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "LoRA Voice Eval Report" in content
    assert "N/A (deferred)" in content


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_check_hardware(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--check-hardware"])
    hw = {"gpu_available": False, "vram_gb": 0.0, "sufficient": False, "note": "no nvidia-smi"}
    with patch(f"{_LPL}._check_hardware", return_value=hw):
        main()
    out = capsys.readouterr().out
    assert "GPU" in out
    assert "no nvidia-smi" in out


def test_main_check_hardware_sufficient_no_note(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog", "--check-hardware"])
    hw = {"gpu_available": True, "vram_gb": 10.0, "sufficient": True, "note": ""}
    with patch(f"{_LPL}._check_hardware", return_value=hw):
        main()
    out = capsys.readouterr().out
    assert "10.0" in out


def test_main_step_prep(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", [
        "prog", "--step", "prep",
        "--corpus-dir", str(tmp_path / "corpus"),
        "--dataset", str(tmp_path / "train.jsonl"),
    ])
    with patch(f"{_LPL}._step_prep") as mock_prep:
        main()
    mock_prep.assert_called_once()


def test_main_step_train(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "--step", "train"])
    with patch(f"{_LPL}._step_train") as mock_train:
        main()
    mock_train.assert_called_once()


def test_main_step_eval(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["prog", "--step", "eval"])
    with patch(f"{_LPL}._step_eval") as mock_eval:
        main()
    mock_eval.assert_called_once()


def test_main_no_step_prints_help(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["prog"])
    main()  # prints help, does not raise
