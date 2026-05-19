"""Entity extraction for Calliope char_memory — ported from Vesta memory_tree.

Adapted for RP Italian/English fantasy context:
- spacy optional (en_core_web_sm), falls back to regex
- Extended patterns for Italian proper names + fantasy context
"""
from __future__ import annotations

import re
import warnings
from typing import Any

# Regex patterns (always available fallback)
_PATTERN_PERSON = re.compile(
    r"\b[A-ZÀÈÌÒÙÂÊÎÔÛÄËÏÖÜ][a-zàèìòùäëïöüâêîôû]+(?:\s+[A-ZÀÈÌÒÙÂÊÎÔÛÄËÏÖÜ][a-zàèìòùäëïöüâêîôû]+)*\b"
)
_PATTERN_LOCATION = re.compile(
    r"\b(?:a|al|alla|nel|nella|dal|della|di)\s+([A-ZÀÈÌÒÙ][a-zàèìòùäëïöü]+(?:\s+[A-ZÀÈÌÒÙ][a-zàèìòùäëïöü]+)*)\b"
)
_PATTERN_ORG = re.compile(r"\b[A-Z]{2,12}\b")
_PATTERN_DATE_ISO = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
_PATTERN_TIME = re.compile(r"\b(?:ore\s+)?\d{1,2}:\d{2}\b")

# RP-specific stop tokens to exclude from PERSON extraction
_STOP_TOKENS = {
    "The", "An", "A", "In", "At", "On", "Of", "For", "To", "And", "Or",
    "But", "He", "She", "It", "They", "We", "You", "His", "Her", "Their",
    "Il", "La", "Lo", "Le", "Gli", "Un", "Una", "Del", "Della", "Degli",
    "Delle", "Dei", "Nelle", "Nella", "Nel", "Nello", "NaN", "None",
    "True", "False", "Tier", "Phase", "Level", "Scene",
}


class EntityLinker:
    """Extract named entities; spacy optional, regex fallback always available."""

    def __init__(self, model: str = "en_core_web_sm") -> None:
        self._nlp: Any = None
        try:
            import spacy  # type: ignore[import-untyped]
            self._nlp = spacy.load(model)
        except Exception:
            warnings.warn(
                "spacy not available — using regex entity extraction (Calliope RP mode)",
                RuntimeWarning,
                stacklevel=2,
            )

    def extract_entities(self, text: str) -> list[dict[str, str]]:
        """Return list of {name, label} dicts extracted from text."""
        if self._nlp is not None:
            doc = self._nlp(text)
            seen: set[tuple[str, str]] = set()
            results: list[dict[str, str]] = []
            for ent in doc.ents:
                key = (ent.text.strip(), ent.label_)
                if key not in seen and key[0] not in _STOP_TOKENS:
                    seen.add(key)
                    results.append({"name": key[0], "label": ent.label_})
            return results
        return self._regex_extract(text)

    def link_to_fact(
        self, fact_id: str, entities: list[dict[str, str]]
    ) -> list[dict[str, str]]:
        for ent in entities:
            ent["fact_id"] = fact_id
        return entities

    def _regex_extract(self, text: str) -> list[dict[str, str]]:
        seen: set[tuple[str, str]] = set()
        results: list[dict[str, str]] = []

        for m in _PATTERN_DATE_ISO.finditer(text):
            _add(results, seen, m.group(), "DATE")
        for m in _PATTERN_TIME.finditer(text):
            _add(results, seen, m.group(), "TIME")
        for m in _PATTERN_LOCATION.finditer(text):
            _add(results, seen, m.group(1), "LOC")
        for m in _PATTERN_PERSON.finditer(text):
            name = m.group()
            if name not in _STOP_TOKENS and len(name) > 2:
                _add(results, seen, name, "PERSON")
        stripped = _PATTERN_PERSON.sub("", text)
        for m in _PATTERN_ORG.finditer(stripped):
            token = m.group()
            if token not in _STOP_TOKENS and token not in {"NaN", "None", "True", "False"}:
                _add(results, seen, token, "ORG")

        return results


def _add(
    results: list[dict[str, str]],
    seen: set[tuple[str, str]],
    name: str,
    label: str,
) -> None:
    key = (name.strip(), label)
    if key not in seen and key[0]:
        seen.add(key)
        results.append({"name": key[0], "label": label})


def extract_entities_for_fact(
    text: str,
    fact_id: str,
    linker: EntityLinker | None = None,
) -> list[dict[str, str]]:
    """Convenience: extract entities and attach fact_id."""
    if linker is None:
        linker = EntityLinker()
    entities = linker.extract_entities(text)
    return linker.link_to_fact(fact_id, entities)
