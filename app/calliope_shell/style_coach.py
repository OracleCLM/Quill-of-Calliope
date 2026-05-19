"""
Style Coach — anti-cliché linter + operator voice-style similarity scorer.

Usage:
    from app.calliope_shell.style_coach import lint_scene_output
    report = lint_scene_output(text)

CLI:
    python -m app.calliope_shell.style_coach <scene_file> [--threshold MED]
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml

_LEXICON_PATH = Path(__file__).parents[2] / "data" / "anti_gpt_lexicon.yaml"
_VOICE_SAMPLES_PATH = Path(__file__).parents[2] / "data" / "operator_voice_samples.txt"
_SEVERITY_ORDER = {"LOW": 0, "MED": 1, "HIGH": 2}

# ── Sentence splitter ─────────────────────────────────────────────────────────

_SENT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


# ── Lexicon helpers ───────────────────────────────────────────────────────────

def _load_lexicon() -> list[dict]:
    with open(_LEXICON_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["phrases"]


# ── Stylometric similarity (TF-IDF cosine, sklearn) ───────────────────────────

def _load_voice_samples() -> list[str]:
    if not _VOICE_SAMPLES_PATH.exists():
        return []
    raw = _VOICE_SAMPLES_PATH.read_text(encoding="utf-8").split("---")
    return [s.strip() for s in raw if s.strip()]


def _compute_style_drift(text: str, samples: list[str]) -> float | None:
    """Return cosine distance [0..1] between text and operator centroid.

    Returns None if sklearn unavailable or corpus empty.
    """
    if not samples:
        return None
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: PLC0415
        from sklearn.metrics.pairwise import cosine_similarity  # noqa: PLC0415
        import numpy as np  # noqa: PLC0415

        corpus = samples + [text]
        vec = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
        tfidf = vec.fit_transform(corpus)
        centroid = np.asarray(tfidf[:-1].mean(axis=0))
        scene_vec = np.asarray(tfidf[-1].toarray())
        sim = float(cosine_similarity(centroid, scene_vec)[0][0])
        return round(1.0 - sim, 4)  # drift = 1 - similarity
    except Exception:
        return None


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class LintFinding:
    sentence_idx: int
    sentence: str
    type: str          # "cliche_hit" | "style_drift"
    severity: str      # HIGH | MED | LOW
    category: str
    pattern: str
    reason: str
    suggestion: str


@dataclass
class LintReport:
    findings: List[LintFinding] = field(default_factory=list)
    style_drift_score: float | None = None
    cliche_count: int = 0
    high_count: int = 0
    med_count: int = 0
    low_count: int = 0

    def summary(self) -> str:
        lines = [
            f"Cliché findings: {self.cliche_count} "
            f"(HIGH={self.high_count} MED={self.med_count} LOW={self.low_count})",
        ]
        if self.style_drift_score is not None:
            lines.append(f"Style drift from operator centroid: {self.style_drift_score:.3f} (0=identical, 1=max drift)")
        return "\n".join(lines)


# ── Core linter ───────────────────────────────────────────────────────────────

def lint_scene_output(
    text: str,
    severity_threshold: str = "MED",
    operator_corpus_features: list[str] | None = None,
) -> LintReport:
    """Lint scene text for GPT clichés + operator voice drift.

    Args:
        text: Scene text to lint.
        severity_threshold: Minimum severity to flag ("LOW", "MED", "HIGH").
        operator_corpus_features: Optional override for voice samples.

    Returns:
        LintReport with per-sentence findings and aggregate stats.
    """
    report = LintReport()
    lexicon = _load_lexicon()
    sentences = _split_sentences(text)
    threshold_level = _SEVERITY_ORDER[severity_threshold]

    for idx, sent in enumerate(sentences):
        for entry in lexicon:
            sev = entry["severity"]
            if _SEVERITY_ORDER[sev] < threshold_level:
                continue
            if re.search(entry["pattern"], sent, re.IGNORECASE):
                finding = LintFinding(
                    sentence_idx=idx,
                    sentence=sent,
                    type="cliche_hit",
                    severity=sev,
                    category=entry.get("category", "unknown"),
                    pattern=entry["pattern"],
                    reason=entry["reason"],
                    suggestion="Rewrite without this phrase.",
                )
                report.findings.append(finding)
                report.cliche_count += 1
                if sev == "HIGH":
                    report.high_count += 1
                elif sev == "MED":
                    report.med_count += 1
                else:
                    report.low_count += 1

    # Stylometric drift
    samples = operator_corpus_features if operator_corpus_features is not None else _load_voice_samples()
    drift = _compute_style_drift(text, samples)
    if drift is not None:
        report.style_drift_score = drift
        if drift > 0.7:
            report.findings.append(LintFinding(
                sentence_idx=-1,
                sentence="(full text)",
                type="style_drift",
                severity="MED",
                category="stylometric",
                pattern="cosine_drift",
                reason=f"Style drift {drift:.3f} > 0.7 threshold vs operator corpus",
                suggestion="Review overall register; compare to operator voice samples.",
            ))

    return report


# ── CLI entry point ───────────────────────────────────────────────────────────

def _main() -> None:
    import argparse  # noqa: PLC0415

    parser = argparse.ArgumentParser(description="Style Coach — anti-cliché linter")
    parser.add_argument("scene_file", type=Path, help="Scene .md file to lint")
    parser.add_argument("--threshold", default="MED", choices=["LOW", "MED", "HIGH"])
    args = parser.parse_args()

    text = args.scene_file.read_text(encoding="utf-8")
    report = lint_scene_output(text, severity_threshold=args.threshold)

    print(report.summary())
    if report.findings:
        print()
        for f in report.findings:
            label = f"[{f.severity}][{f.category}]" if f.type == "cliche_hit" else "[DRIFT]"
            loc = f"sent#{f.sentence_idx}" if f.sentence_idx >= 0 else "full-text"
            print(f"  {label} {loc}: {f.reason}")
            if f.sentence_idx >= 0:
                print(f"    > {f.sentence[:100]}")
    else:
        print("  No findings.")


if __name__ == "__main__":
    sys.exit(_main())
