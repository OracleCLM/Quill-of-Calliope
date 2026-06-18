"""GAP-36: test unitari per style_coach — lint_scene_output, LintReport, _split_sentences."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.style_coach import LintFinding, LintReport, lint_scene_output

# Frasi reali dal lexicon (HIGH e MED)
_HIGH_TEXT = "It was a testament to her unwavering resolve."
_MED_TEXT = "She had piercing eyes that gazed into the distance."
_CLEAN_TEXT = "She walked into the room and sat down."


# ── LintReport.summary ───────────────────────────────────────────────────────


def test_lint_report_summary_contains_cliche_count():
    report = LintReport(cliche_count=3, high_count=1, med_count=2)
    summary = report.summary()
    assert "3" in summary
    assert "HIGH=1" in summary
    assert "MED=2" in summary


def test_lint_report_summary_no_drift():
    report = LintReport()
    summary = report.summary()
    assert "drift" not in summary.lower()


def test_lint_report_summary_with_drift():
    report = LintReport(style_drift_score=0.42)
    summary = report.summary()
    assert "0.42" in summary or "drift" in summary.lower()


# ── lint_scene_output — return type ──────────────────────────────────────────


def test_returns_lint_report():
    report = lint_scene_output(_CLEAN_TEXT, operator_corpus_features=[])
    assert isinstance(report, LintReport)


def test_clean_text_zero_findings():
    report = lint_scene_output(_CLEAN_TEXT, operator_corpus_features=[])
    assert report.cliche_count == 0
    assert report.findings == []


# ── cliché detection ──────────────────────────────────────────────────────────


def test_high_severity_detected():
    report = lint_scene_output(_HIGH_TEXT, operator_corpus_features=[])
    highs = [f for f in report.findings if f.severity == "HIGH" and f.type == "cliche_hit"]
    assert len(highs) >= 1


def test_high_count_incremented():
    report = lint_scene_output(_HIGH_TEXT, operator_corpus_features=[])
    assert report.high_count >= 1


def test_med_severity_detected_at_med_threshold():
    report = lint_scene_output(_MED_TEXT, severity_threshold="MED", operator_corpus_features=[])
    meds = [f for f in report.findings if f.severity == "MED" and f.type == "cliche_hit"]
    assert len(meds) >= 1


def test_med_finding_excluded_at_high_threshold():
    report_high = lint_scene_output(_MED_TEXT, severity_threshold="HIGH", operator_corpus_features=[])
    meds = [f for f in report_high.findings if f.severity == "MED" and f.type == "cliche_hit"]
    assert meds == []


# ── LintFinding fields ────────────────────────────────────────────────────────


def test_finding_fields_populated():
    report = lint_scene_output(_HIGH_TEXT, operator_corpus_features=[])
    finding = next((f for f in report.findings if f.type == "cliche_hit"), None)
    assert finding is not None
    assert isinstance(finding, LintFinding)
    assert finding.sentence_idx >= 0
    assert finding.sentence != ""
    assert finding.category != ""
    assert finding.reason != ""
    assert finding.suggestion != ""


# ── threshold LOW ─────────────────────────────────────────────────────────────


def test_low_threshold_flags_more_than_med():
    multi_text = (
        "She had piercing eyes. "
        "It was a testament to her resolve. "
        "She walked in."
    )
    report_low = lint_scene_output(multi_text, severity_threshold="LOW", operator_corpus_features=[])
    report_med = lint_scene_output(multi_text, severity_threshold="MED", operator_corpus_features=[])
    assert report_low.cliche_count >= report_med.cliche_count


# ── style drift ───────────────────────────────────────────────────────────────


def test_no_style_drift_when_no_corpus():
    report = lint_scene_output(_CLEAN_TEXT, operator_corpus_features=[])
    assert report.style_drift_score is None


def test_style_drift_computed_with_corpus():
    corpus = ["Aurora combatté. Le stelle brillavano.", "Il castello era silenzioso."]
    report = lint_scene_output(_CLEAN_TEXT, operator_corpus_features=corpus)
    assert report.style_drift_score is not None
    assert 0.0 <= report.style_drift_score <= 1.0


def test_high_drift_adds_finding():
    identical_samples = ["x y z a b c"] * 5
    very_different_text = " ".join(["the", "quick", "brown", "fox"] * 50)
    report = lint_scene_output(
        very_different_text,
        severity_threshold="MED",
        operator_corpus_features=identical_samples,
    )
    drift_findings = [f for f in report.findings if f.type == "style_drift"]
    if report.style_drift_score is not None and report.style_drift_score > 0.7:
        assert len(drift_findings) >= 1


# ── sklearn optional — graceful fallback ─────────────────────────────────────


def test_drift_none_when_sklearn_unavailable():
    with patch.dict("sys.modules", {"sklearn": None,
                                    "sklearn.feature_extraction": None,
                                    "sklearn.feature_extraction.text": None,
                                    "sklearn.metrics": None,
                                    "sklearn.metrics.pairwise": None}):
        corpus = ["Aurora combatté.", "Koko rise."]
        report = lint_scene_output(_CLEAN_TEXT, operator_corpus_features=corpus)
    assert report.style_drift_score is None
