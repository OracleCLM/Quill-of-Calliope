"""
Anti-cliché post-LLM filter.

Usage:
    from scripts.style_filter import filter_response
    cleaned, report = filter_response(llm_output, severity_threshold="MED")
"""

import re
from pathlib import Path
from typing import Dict, List, Tuple

import yaml

_BLACKLIST_PATH = Path(__file__).parent.parent / "data" / "anti_cliche_blacklist.yaml"
_SEVERITY_ORDER = {"LOW": 0, "MED": 1, "HIGH": 2}


def load_blacklist() -> List[Dict]:
    with open(_BLACKLIST_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)["phrases"]


def filter_response(text: str, severity_threshold: str = "MED") -> Tuple[str, List[Dict]]:
    """Return (cleaned_text, list_of_findings).

    Findings keys: pattern, severity, reason, count, action ('stripped'|'warned').
    HIGH always stripped. MED stripped if threshold<=MED. LOW noted only.
    """
    blacklist = load_blacklist()
    findings: List[Dict] = []
    cleaned = text
    threshold_level = _SEVERITY_ORDER[severity_threshold]

    for entry in blacklist:
        pattern = entry["pattern"]
        severity = entry["severity"]
        matches = list(re.finditer(pattern, cleaned, re.IGNORECASE))
        if not matches:
            continue
        sev_level = _SEVERITY_ORDER[severity]
        action = "stripped" if sev_level >= threshold_level else "warned"
        findings.append({
            "pattern": pattern,
            "severity": severity,
            "reason": entry["reason"],
            "count": len(matches),
            "action": action,
        })
        if action == "stripped":
            cleaned = re.sub(pattern, "", cleaned, flags=re.IGNORECASE)
            cleaned = re.sub(r"\s+", " ", cleaned)

    return cleaned.strip(), findings
