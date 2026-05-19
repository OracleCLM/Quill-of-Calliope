import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from style_filter import filter_response, load_blacklist


def test_blacklist_loads():
    bl = load_blacklist()
    assert len(bl) >= 5
    assert all("pattern" in e and "severity" in e for e in bl)


def test_high_severity_stripped():
    text = "His sword exuded silent menace as he approached."
    cleaned, findings = filter_response(text, severity_threshold="HIGH")
    assert "exuded silent menace" not in cleaned.lower()
    assert any(f["severity"] == "HIGH" and f["action"] == "stripped" for f in findings)


def test_med_warned_only_at_high_threshold():
    text = "She had an air of mystery about her."
    cleaned, findings = filter_response(text, severity_threshold="HIGH")
    # At HIGH threshold, MED is only warned (not stripped)
    assert any(f["severity"] == "MED" and f["action"] == "warned" for f in findings)
    assert "an air of mystery" in cleaned.lower()


def test_clean_text_no_findings():
    text = "Aurora drew her blade and faced the dawn."
    cleaned, findings = filter_response(text)
    assert cleaned == text
    assert findings == []


def test_med_stripped_at_med_threshold():
    text = "The silence was deafening in the hall."
    cleaned, findings = filter_response(text, severity_threshold="MED")
    assert any(f["severity"] == "MED" and f["action"] == "stripped" for f in findings)
    assert "deafening" not in cleaned.lower()


def test_multiple_findings_report():
    text = (
        "His sword exuded silent menace. "
        "Her piercing gaze met his across the room. "
        "It was an intimidating masterpiece of craft."
    )
    cleaned, findings = filter_response(text, severity_threshold="HIGH")
    assert len(findings) >= 2
    stripped = [f for f in findings if f["action"] == "stripped"]
    assert len(stripped) >= 2
