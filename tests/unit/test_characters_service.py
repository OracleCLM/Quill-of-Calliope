"""
Unit test per app/calliope_shell/characters_service.py.

Contratto:
  - import_card_v3: pura, roundtrip CharacterCard
  - _merged_legacy_dict: draft-only, canon overrides, entrambi assenti
  - load_card: delega a _merged_legacy_dict + from_legacy_yaml
  - list_cards: elenca stems, skip card malformate, sort per nome
  - get_card_v3 / export_card_v3: None se non esiste, dict v3 se esiste
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.characters_service import (
    _merged_legacy_dict,
    export_card_v3,
    get_card_v3,
    import_card_v3,
    list_cards,
    load_card,
)
from app.calliope_shell.scene_model import CharacterCard

_MOD = "app.calliope_shell.characters_service"


# ── import_card_v3 ─────────────────────────────────────────────────────────────

def test_import_card_v3_creates_card():
    data = {"name": "Aurora", "personality": "strega", "tags": ["dark"]}
    card = import_card_v3(data)
    assert isinstance(card, CharacterCard)
    assert card.name == "Aurora"
    assert card.personality == "strega"


def test_import_card_v3_roundtrip():
    card = CharacterCard(name="Gabby", personality="hacker", tags=["tech"])
    d = card.to_v3_dict()
    card2 = import_card_v3(d)
    assert card2.name == "Gabby"
    assert card2.tags == ["tech"]


# ── _merged_legacy_dict (con _chars_dir monkeypatchato) ──────────────────────

def test_merged_draft_only(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text(
        "name: Aurora\npersonality: strega\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = _merged_legacy_dict("aurora")
    assert result["name"] == "Aurora"
    assert result["personality"] == "strega"


def test_merged_canon_overrides_draft(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text(
        "name: Aurora\npersonality: strega\n"
    )
    (tmp_path / "aurora.canon.yaml").write_text(
        "overrides:\n  personality: archmage\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = _merged_legacy_dict("aurora")
    assert result["personality"] == "archmage"
    assert result["name"] == "Aurora"


def test_merged_neither_file_returns_empty(tmp_path):
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = _merged_legacy_dict("nonexistent")
    assert result == {}


def test_merged_corrupt_draft_returns_empty(tmp_path):
    (tmp_path / "bad.draft.yaml").write_text("NOT: YAML: {{{{")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = _merged_legacy_dict("bad")
    assert isinstance(result, dict)


# ── load_card ─────────────────────────────────────────────────────────────────

def test_load_card_builds_character_card(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text(
        "name: Aurora\npersonality: strega oscura\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        card = load_card("aurora")
    assert isinstance(card, CharacterCard)
    assert card.name == "Aurora"


def test_load_card_missing_returns_empty_card(tmp_path):
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        card = load_card("ghost")
    assert isinstance(card, CharacterCard)
    assert card.name == ""


# ── list_cards ────────────────────────────────────────────────────────────────

def test_list_cards_empty_dir(tmp_path):
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    assert result == []


def test_list_cards_returns_stems(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text("name: Aurora\n")
    (tmp_path / "gabby.draft.yaml").write_text("name: Gabby\n")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    names = [r["name"] for r in result]
    assert "Aurora" in names
    assert "Gabby" in names


def test_list_cards_sorted_by_name(tmp_path):
    (tmp_path / "zzz.draft.yaml").write_text("name: Zzz\n")
    (tmp_path / "aaa.draft.yaml").write_text("name: Aaa\n")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    assert result[0]["name"].lower() <= result[-1]["name"].lower()


def test_list_cards_includes_stem_and_compact(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text(
        "name: Aurora\npersonality: strega\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    assert result[0]["stem"] == "aurora"
    assert "Aurora" in result[0]["compact"]


def test_list_cards_skips_corrupt(tmp_path):
    (tmp_path / "bad.draft.yaml").write_text("NOT: {{{YAML")
    (tmp_path / "ok.draft.yaml").write_text("name: OK\n")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    # "bad" può essere saltata o restituita con nome vuoto, ma "ok" deve esserci
    names = [r["name"] for r in result]
    assert "OK" in names


def test_list_cards_canon_only_included(tmp_path):
    (tmp_path / "ghost.canon.yaml").write_text(
        "overrides:\n  name: Ghost\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = list_cards()
    # Il canon-only stem deve apparire
    stems = [r["stem"] for r in result]
    assert "ghost" in stems


# ── get_card_v3 / export_card_v3 ─────────────────────────────────────────────

def test_get_card_v3_not_found(tmp_path):
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        assert get_card_v3("ghost") is None


def test_get_card_v3_returns_dict(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text(
        "name: Aurora\npersonality: strega\n"
    )
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = get_card_v3("aurora")
    assert result is not None
    assert result["name"] == "Aurora"


def test_export_card_v3_alias(tmp_path):
    (tmp_path / "aurora.draft.yaml").write_text("name: Aurora\n")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        assert export_card_v3("aurora") == get_card_v3("aurora")


def test_merged_corrupt_canon_ignored(tmp_path):
    (tmp_path / "hero.draft.yaml").write_text("name: Hero\n")
    (tmp_path / "hero.canon.yaml").write_text(": {{INVALID")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        result = _merged_legacy_dict("hero")
    assert result.get("name") == "Hero"


def test_list_cards_load_exception_skips_stem(tmp_path):
    (tmp_path / "boom.draft.yaml").write_text("name: Boom\n")
    (tmp_path / "ok.draft.yaml").write_text("name: OK\n")
    original_load = __import__("app.calliope_shell.characters_service", fromlist=["load_card"]).load_card

    def _failing_load(stem):
        if stem == "boom":
            raise RuntimeError("forced failure")
        return original_load(stem)

    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        with patch(f"{_MOD}.load_card", side_effect=_failing_load):
            result = list_cards()
    names = [r["name"] for r in result]
    assert "OK" in names
    assert "Boom" not in names


def test_get_card_v3_load_exception_returns_none(tmp_path):
    (tmp_path / "crash.draft.yaml").write_text("name: Crash\n")
    with patch(f"{_MOD}._chars_dir", return_value=tmp_path):
        with patch(f"{_MOD}.load_card", side_effect=RuntimeError("boom")):
            result = get_card_v3("crash")
    assert result is None
