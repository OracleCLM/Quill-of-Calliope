"""Unit test per scripts/style_filter.py (base zai-glm, corretto Claude).

load_blacklist() mockato per evitare dipendenza dal file YAML reale.
"""
from __future__ import annotations

from unittest.mock import patch

from scripts.style_filter import filter_response

_BLACKLIST = [
    {"pattern": "stupid", "severity": "HIGH", "reason": "Insult"},
    {"pattern": "darn", "severity": "MED", "reason": "Mild profanity"},
    {"pattern": "lazy", "severity": "LOW", "reason": "Unprofessional"},
    {"pattern": r"dumb\s+idea", "severity": "HIGH", "reason": "Criticism"},
]

_P = "scripts.style_filter.load_blacklist"


def test_empty_text():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("")
    assert cleaned == ""
    assert findings == []


def test_no_matches():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("Hello world")
    assert cleaned == "Hello world"
    assert findings == []


def test_high_severity_stripped_default_threshold():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("A stupid remark here")
    assert "stupid" not in cleaned.lower()
    assert len(findings) == 1
    assert findings[0]["action"] == "stripped"
    assert findings[0]["severity"] == "HIGH"


def test_med_severity_stripped_default_threshold():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("Darn it")
    assert "darn" not in cleaned.lower()
    assert findings[0]["action"] == "stripped"
    assert findings[0]["severity"] == "MED"


def test_low_severity_warned_default_threshold():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("He is lazy")
    assert "lazy" in cleaned.lower()  # warned → non rimosso
    assert findings[0]["action"] == "warned"
    assert findings[0]["severity"] == "LOW"


def test_threshold_high_med_severity_warned():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("Darn it", severity_threshold="HIGH")
    assert "darn" in cleaned.lower()  # threshold=HIGH → MED solo warned
    assert findings[0]["action"] == "warned"


def test_threshold_low_strips_low_severity():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("He is lazy", severity_threshold="LOW")
    assert "lazy" not in cleaned.lower()
    assert findings[0]["action"] == "stripped"


def test_multiple_matches_count():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("stupid stupid stupid")
    assert cleaned == ""
    assert findings[0]["count"] == 3


def test_whitespace_collapsed_after_strip():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("This is stupid stuff")
    assert "  " not in cleaned  # doppio spazio collassato
    assert "stupid" not in cleaned.lower()


def test_case_insensitive():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, _ = filter_response("StUpId")
    assert cleaned == ""


def test_regex_pattern():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("That is a dumb idea here")
    assert "dumb" not in cleaned.lower()
    assert findings[0]["pattern"] == r"dumb\s+idea"


def test_mixed_severities_high_stripped_low_kept():
    with patch(_P, return_value=_BLACKLIST):
        cleaned, findings = filter_response("Stupid lazy person")
    assert "stupid" not in cleaned.lower()
    assert "lazy" in cleaned.lower()
    assert len(findings) == 2
    actions = {f["action"] for f in findings}
    assert "stripped" in actions
    assert "warned" in actions
