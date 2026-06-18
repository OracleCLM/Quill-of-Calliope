"""GAP-32: test unitari per entity_linker — regex fallback, link_to_fact, extract_entities_for_fact."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.entity_linker import EntityLinker, extract_entities_for_fact


def _linker_no_spacy() -> EntityLinker:
    linker = EntityLinker.__new__(EntityLinker)
    linker._nlp = None
    return linker


# --- regex extract — DATE ---------------------------------------------------


def test_regex_extracts_iso_date():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("Accadde il 2026-06-18 a Midgard.")
    labels = {e["label"] for e in ents}
    names = {e["name"] for e in ents}
    assert "DATE" in labels
    assert "2026-06-18" in names


# --- regex extract — TIME ---------------------------------------------------


def test_regex_extracts_time():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("Alle 14:30 Aurora arrivò.")
    labels = {e["label"] for e in ents}
    assert "TIME" in labels


# --- regex extract — PERSON -------------------------------------------------


def test_regex_extracts_person():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("Aurora combatté con Tingyun.")
    names = {e["name"] for e in ents}
    assert "Aurora" in names or "Tingyun" in names


def test_regex_deduplicates_person():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("Aurora parlò. Aurora rise.")
    person_ents = [e for e in ents if e["name"] == "Aurora"]
    assert len(person_ents) == 1


def test_regex_skips_stop_tokens():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("The castle fell. In the darkness.")
    names = {e["name"] for e in ents}
    assert "The" not in names
    assert "In" not in names


# --- regex extract — LOCATION -----------------------------------------------


def test_regex_extracts_location():
    linker = _linker_no_spacy()
    ents = linker.extract_entities("Arrivarono nel Castello della Morte.")
    labels = {e["label"] for e in ents}
    assert "LOC" in labels


# --- link_to_fact ------------------------------------------------------------


def test_link_to_fact_attaches_fact_id():
    linker = _linker_no_spacy()
    entities = [{"name": "Aurora", "label": "PERSON"}]
    linked = linker.link_to_fact("fact-001", entities)
    assert linked[0]["fact_id"] == "fact-001"


def test_link_to_fact_modifies_in_place():
    linker = _linker_no_spacy()
    entities = [{"name": "X", "label": "ORG"}, {"name": "Y", "label": "PERSON"}]
    result = linker.link_to_fact("fact-XYZ", entities)
    assert all(e["fact_id"] == "fact-XYZ" for e in result)


# --- extract_entities_for_fact ----------------------------------------------


def test_extract_entities_for_fact_returns_list():
    ents = extract_entities_for_fact("Aurora è a Midgard.", "fact-42")
    assert isinstance(ents, list)


def test_extract_entities_for_fact_attaches_fact_id():
    ents = extract_entities_for_fact("Aurora incontrò Koko nel 2026-01-01.", "fact-99")
    assert all("fact_id" in e for e in ents)
    assert all(e["fact_id"] == "fact-99" for e in ents)


def test_extract_entities_for_fact_creates_default_linker():
    ents = extract_entities_for_fact("Il 2025-12-31 ci fu una festa.", "f1", linker=None)
    assert any(e["label"] == "DATE" for e in ents)
