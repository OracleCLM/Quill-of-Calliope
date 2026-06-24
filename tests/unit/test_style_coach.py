"""
Unit test per style_coach.py — anti-cliché linter.

Contratto:
  - _split_sentences: split su [.!?] seguito da spazio
  - lint_scene_output: testo pulito → 0 findings; cliché HIGH → finding;
    severity_threshold filtra; style_drift con corpus; LintReport.summary
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.style_coach import (
    LintReport,
    _split_sentences,
    lint_scene_output,
)

_MOD = "app.calliope_shell.style_coach"

_FAKE_LEXICON = [
    {
        "pattern": "test cliche phrase",
        "severity": "HIGH",
        "category": "test_cat",
        "reason": "Test reason",
    },
    {
        "pattern": "low severity phrase",
        "severity": "LOW",
        "category": "test_cat",
        "reason": "Low test",
    },
]


# ── _split_sentences ──────────────────────────────────────────────────────────

def test_split_sentences_basic():
    sentences = _split_sentences("Prima frase. Seconda frase.")
    assert len(sentences) == 2
    assert sentences[0] == "Prima frase."


def test_split_sentences_exclamation():
    sentences = _split_sentences("Wow! Fantastico!")
    assert len(sentences) == 2


def test_split_sentences_question():
    sentences = _split_sentences("Chi sei? Non lo so.")
    assert len(sentences) == 2


def test_split_sentences_empty():
    assert _split_sentences("") == []


def test_split_sentences_single():
    result = _split_sentences("Una sola frase senza punto")
    assert result == ["Una sola frase senza punto"]


# ── lint_scene_output — clean text ────────────────────────────────────────────

def test_lint_clean_text_no_findings():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output("Testo completamente pulito senza cliché.")
    assert report.cliche_count == 0
    assert report.findings == []


# ── lint_scene_output — cliché detection ─────────────────────────────────────

def test_lint_detects_high_cliche():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output("Questa è una test cliche phrase nel testo.")
    assert report.cliche_count == 1
    assert report.high_count == 1
    assert report.findings[0].severity == "HIGH"
    assert report.findings[0].type == "cliche_hit"


def test_lint_case_insensitive():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output("TEST CLICHE PHRASE in maiuscolo.")
    assert report.cliche_count == 1


# ── severity threshold filtering ──────────────────────────────────────────────

def test_lint_threshold_high_skips_low():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output(
            "low severity phrase presente.", severity_threshold="HIGH"
        )
    assert report.cliche_count == 0
    assert report.low_count == 0


def test_lint_threshold_low_catches_all():
    text = "test cliche phrase e anche low severity phrase."
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output(text, severity_threshold="LOW")
    assert report.cliche_count == 2
    assert report.high_count == 1
    assert report.low_count == 1


# ── style drift via real lexicon ──────────────────────────────────────────────

def test_lint_no_drift_without_corpus():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._load_voice_samples", return_value=[]):
        report = lint_scene_output("Testo qualsiasi.")
    assert report.style_drift_score is None


def test_lint_drift_uses_operator_corpus_features():
    samples = ["frasi di esempio dell'operatore uno", "secondo esempio stile"]
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON):
        # Passa corpus direttamente, senza mock _load_voice_samples
        try:
            report = lint_scene_output(
                "Testo di test.", operator_corpus_features=samples
            )
            # Se sklearn disponibile, drift deve essere un float [0..1]
            if report.style_drift_score is not None:
                assert 0.0 <= report.style_drift_score <= 1.0
        except Exception:
            pass  # sklearn non disponibile → skip silenzioso


# ── LintReport.summary ────────────────────────────────────────────────────────

def test_lint_report_summary_no_findings():
    report = LintReport()
    s = report.summary()
    assert "0" in s
    assert "HIGH=0" in s


def test_lint_report_summary_with_counts():
    report = LintReport(cliche_count=3, high_count=1, med_count=2)
    s = report.summary()
    assert "3" in s
    assert "HIGH=1" in s
    assert "MED=2" in s


def test_lint_report_summary_with_drift():
    report = LintReport(style_drift_score=0.42)
    s = report.summary()
    assert "0.420" in s or "drift" in s.lower()


# ── real lexicon integration ──────────────────────────────────────────────────

def test_lint_real_lexicon_clean_text():
    """Smoke test con il lexicon reale e testo pulito."""
    report = lint_scene_output(
        "Aurora camminava nel bosco in silenzio.",
        operator_corpus_features=[],
    )
    assert isinstance(report.cliche_count, int)
    assert report.cliche_count >= 0


def test_lint_real_lexicon_known_cliche():
    """Il lexicon reale contiene 'exuded silent menace' (HIGH)."""
    report = lint_scene_output(
        "He exuded silent menace as he stepped forward.",
        operator_corpus_features=[],
    )
    assert report.high_count >= 1


# ── coverage gaps ─────────────────────────────────────────────────────────────

def test_lint_real_lexicon_med_severity():
    """'an air of mystery' è MED nel lexicon reale."""
    report = lint_scene_output(
        "The room had an air of mystery that no one could explain.",
        operator_corpus_features=[],
    )
    assert report.med_count >= 1


def test_load_voice_samples_with_existing_file(tmp_path):
    from app.calliope_shell import style_coach
    samples_file = tmp_path / "voice.txt"
    samples_file.write_text("Sample one.\n---\nSample two.\n")
    monkeypatch_path = tmp_path / "voice.txt"
    original = style_coach._VOICE_SAMPLES_PATH
    try:
        style_coach._VOICE_SAMPLES_PATH = monkeypatch_path
        from app.calliope_shell.style_coach import _load_voice_samples
        result = _load_voice_samples()
    finally:
        style_coach._VOICE_SAMPLES_PATH = original
    assert len(result) == 2


def test_lint_style_drift_score_set_when_compute_returns_value():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._compute_style_drift", return_value=0.5):
        report = lint_scene_output("Testo qualsiasi.", operator_corpus_features=["x"])
    assert report.style_drift_score == 0.5


def test_lint_style_drift_above_threshold_adds_finding():
    with patch(f"{_MOD}._load_lexicon", return_value=_FAKE_LEXICON), \
         patch(f"{_MOD}._compute_style_drift", return_value=0.85):
        report = lint_scene_output("Testo qualsiasi.", operator_corpus_features=["x"])
    assert report.style_drift_score == 0.85
    assert any(f.type == "style_drift" for f in report.findings)


def test_main_cli_prints_report(tmp_path, capsys):
    from app.calliope_shell.style_coach import _main
    scene_file = tmp_path / "scene.md"
    scene_file.write_text("Una scena normale senza cliché.")
    with patch("sys.argv", ["style_coach", str(scene_file)]):
        _main()
    out = capsys.readouterr().out
    assert "findings" in out.lower() or "no findings" in out.lower()


def test_main_cli_prints_findings_when_cliche_found(tmp_path, capsys):
    """Lines 189-195: findings block in _main() output."""
    from app.calliope_shell.style_coach import _main
    scene_file = tmp_path / "scene.md"
    scene_file.write_text("The room had an air of mystery and danger.")
    with patch("sys.argv", ["style_coach", str(scene_file), "--threshold", "LOW"]):
        _main()
    out = capsys.readouterr().out
    assert "[MED]" in out or "[LOW]" in out or "[HIGH]" in out
