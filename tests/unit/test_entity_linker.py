"""
Unit test entity_linker.py — regex fallback (spacy opzionale).

Tutti i test usano il fallback regex (spacy non installato o modello assente)
che è il path di produzione in questo environment.
"""
import warnings

import pytest

from app.calliope_shell.entity_linker import EntityLinker, extract_entities_for_fact


@pytest.fixture()
def linker():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return EntityLinker()


# ── Persone ───────────────────────────────────────────────────────────────────

def test_person_en_extracted(linker):
    result = linker.extract_entities("Aurora attacked Sable in the forest.")
    names = [e["name"] for e in result if e["label"] == "PERSON"]
    assert "Aurora" in names
    assert "Sable" in names


def test_person_italian_extracted(linker):
    result = linker.extract_entities("Aurora si mosse verso Katsuro.")
    names = [e["name"] for e in result if e["label"] == "PERSON"]
    assert "Aurora" in names


def test_stop_tokens_excluded(linker):
    result = linker.extract_entities("He looked at The forest.")
    names = [e["name"] for e in result if e["label"] == "PERSON"]
    assert "He" not in names
    assert "The" not in names


def test_short_name_excluded(linker):
    # Nomi ≤2 caratteri devono essere scartati
    result = linker.extract_entities("Al went north.")
    names = [e["name"] for e in result if e["label"] == "PERSON"]
    assert "Al" not in names


# ── Date e orari ──────────────────────────────────────────────────────────────

def test_date_iso_extracted(linker):
    result = linker.extract_entities("The event was on 2024-01-15.")
    labels = {e["label"] for e in result}
    assert "DATE" in labels
    dates = [e["name"] for e in result if e["label"] == "DATE"]
    assert "2024-01-15" in dates


def test_time_extracted(linker):
    result = linker.extract_entities("We meet at 14:30 at the gate.")
    times = [e["name"] for e in result if e["label"] == "TIME"]
    assert "14:30" in times


# ── Luoghi ────────────────────────────────────────────────────────────────────

def test_location_italian_extracted(linker):
    result = linker.extract_entities("Aurora si trovava nel Castello del Nord.")
    locs = [e["name"] for e in result if e["label"] == "LOC"]
    assert any("Castello" in loc for loc in locs)


# ── Deduplicazione ────────────────────────────────────────────────────────────

def test_no_duplicates(linker):
    result = linker.extract_entities("Aurora and Aurora met Sable.")
    aurora_entries = [e for e in result if e["name"] == "Aurora" and e["label"] == "PERSON"]
    assert len(aurora_entries) == 1


# ── Empty/edge cases ─────────────────────────────────────────────────────────

def test_empty_text(linker):
    result = linker.extract_entities("")
    assert result == []


def test_no_entities_in_lowercase(linker):
    result = linker.extract_entities("this is all lowercase text here.")
    persons = [e for e in result if e["label"] == "PERSON"]
    assert len(persons) == 0


# ── link_to_fact ──────────────────────────────────────────────────────────────

def test_link_to_fact_adds_fact_id(linker):
    entities = [{"name": "Aurora", "label": "PERSON"}]
    linked = linker.link_to_fact("fact_42", entities)
    assert linked[0]["fact_id"] == "fact_42"


# ── extract_entities_for_fact (convenience) ───────────────────────────────────

def test_extract_entities_for_fact_attaches_id():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        result = extract_entities_for_fact("Aurora fought Sable.", fact_id="f1")
    persons = [e for e in result if e["label"] == "PERSON"]
    assert all(e["fact_id"] == "f1" for e in persons)
    names = [e["name"] for e in persons]
    assert "Aurora" in names
