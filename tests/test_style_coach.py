import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.calliope_shell.style_coach import LintReport, lint_scene_output, _load_lexicon

try:
    import sklearn  # noqa: F401
    _HAS_SKLEARN = True
except Exception:
    _HAS_SKLEARN = False


# TSC1 — lexicon loads and has minimum phrases
def test_tsc1_lexicon_loads():
    lex = _load_lexicon()
    assert len(lex) >= 10
    for entry in lex:
        assert "pattern" in entry
        assert "severity" in entry
        assert entry["severity"] in ("HIGH", "MED", "LOW")


# TSC2 — positive case: HIGH cliché flagged at HIGH threshold
def test_tsc2_high_cliche_detected():
    text = "His sword exuded silent menace — an intimidating masterpiece of dark craft."
    report = lint_scene_output(text, severity_threshold="HIGH")
    assert report.cliche_count >= 1
    assert report.high_count >= 1
    assert any(f.severity == "HIGH" for f in report.findings)


# TSC3 — negative case: clean text produces no findings
def test_tsc3_clean_text_no_findings():
    text = "She drew her blade. He stepped back. Neither spoke."
    report = lint_scene_output(text, severity_threshold="MED")
    assert report.cliche_count == 0
    assert report.findings == [] or all(f.type == "style_drift" for f in report.findings)


# TSC4 — edge: empty text returns empty report
def test_tsc4_empty_text():
    report = lint_scene_output("", severity_threshold="MED")
    assert report.cliche_count == 0
    assert isinstance(report, LintReport)


# TSC5 — edge: very short text (1 word) does not crash
def test_tsc5_single_word():
    report = lint_scene_output("Aurora.", severity_threshold="LOW")
    assert isinstance(report, LintReport)


# TSC6 — edge: foreign language text (Italian) does not crash, returns report
def test_tsc6_foreign_language():
    text = "Aurora sfoderò la spada. Il silenzio era assoluto. Nessuno si mosse."
    report = lint_scene_output(text, severity_threshold="MED")
    assert isinstance(report, LintReport)
    # Italian text should not trigger English cliché patterns significantly
    assert report.high_count == 0


# TSC7 — operator centroid: style drift computed when samples provided
@pytest.mark.skipif(not _HAS_SKLEARN, reason="sklearn non disponibile in questo env (scipy/py3.13)")
def test_tsc7_style_drift_with_samples():
    samples = [
        "Aurora si mosse senza fretta, la mano sulla guardia.",
        "Il silenzio tra i due era deliberato.",
        "Niente sguardi che trafiggono l'anima. Solo fatti.",
    ]
    text = "Her piercing gaze locked onto his soul with unwavering ferocity."
    report = lint_scene_output(text, severity_threshold="HIGH", operator_corpus_features=samples)
    assert report.style_drift_score is not None
    assert 0.0 <= report.style_drift_score <= 1.0


# TSC8 — style drift None when no samples
def test_tsc8_style_drift_none_without_samples():
    report = lint_scene_output("She moved quickly.", operator_corpus_features=[])
    assert report.style_drift_score is None


# TSC9 — lint_scene_output integration: multiple findings in complex text
def test_tsc9_multiple_findings():
    text = (
        "The air was thick with tension as he entered. "
        "His piercing gaze swept the room. "
        "Every fiber of his being yearned for justice. "
        "It was a testament to his resolve."
    )
    report = lint_scene_output(text, severity_threshold="MED")
    assert report.cliche_count >= 3


# TSC10 — threshold filter: LOW threshold catches more than HIGH
def test_tsc10_threshold_filtering():
    text = (
        "Every step he took was filled with purpose. "
        "The ancient lore of the land surrounded them. "
        "His heart sank with foreboding."
    )
    report_high = lint_scene_output(text, severity_threshold="HIGH")
    report_low = lint_scene_output(text, severity_threshold="LOW")
    assert report_low.cliche_count >= report_high.cliche_count
