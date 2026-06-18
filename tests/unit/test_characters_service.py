"""GAP-37: test unitari per characters_service — _slugify, create_draft, load_card, list_cards, get_card_v3."""

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.characters_service import (
    _slugify,
    create_draft,
    export_card_v3,
    get_card_v3,
    import_card_v3,
    list_cards,
    load_card,
    resolve_character_sheet,
)
from app.calliope_shell.scene_model import CharacterCard


# ── _slugify ─────────────────────────────────────────────────────────────────


def test_slugify_lowercase():
    assert _slugify("Aurora") == "aurora"


def test_slugify_spaces_to_dashes():
    assert _slugify("Aurora Tingyun") == "aurora-tingyun"


def test_slugify_special_chars_stripped():
    assert _slugify("Aria (the Mage)") == "aria-the-mage"


def test_slugify_empty_returns_char():
    assert _slugify("") == "char"


# ── create_draft ─────────────────────────────────────────────────────────────


def test_create_draft_creates_file(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    stem = create_draft("Koko")
    assert (tmp_path / f"{stem}.draft.yaml").exists()


def test_create_draft_returns_stem(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    stem = create_draft("Mao")
    assert stem == "mao"


def test_create_draft_no_overwrite(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    stem1 = create_draft("Aria")
    stem2 = create_draft("Aria")
    assert stem1 != stem2
    assert (tmp_path / f"{stem1}.draft.yaml").exists()
    assert (tmp_path / f"{stem2}.draft.yaml").exists()


def test_create_draft_yaml_has_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    stem = create_draft("Tingyun")
    data = yaml.safe_load((tmp_path / f"{stem}.draft.yaml").read_text())
    assert data["name"] == "Tingyun"


# ── load_card ─────────────────────────────────────────────────────────────────


def test_load_card_returns_character_card(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "aurora.draft.yaml").write_text(
        yaml.dump({"name": "Aurora", "backstory": "guerriera"}), encoding="utf-8"
    )
    card = load_card("aurora")
    assert isinstance(card, CharacterCard)
    assert card.name == "Aurora"


def test_load_card_canon_overrides_draft(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "koko.draft.yaml").write_text(
        yaml.dump({"name": "Koko", "backstory": "draft-backstory"}), encoding="utf-8"
    )
    (tmp_path / "koko.canon.yaml").write_text(
        yaml.dump({"overrides": {"backstory": "canon-backstory"}}), encoding="utf-8"
    )
    card = load_card("koko")
    assert card.description == "canon-backstory"


def test_load_card_missing_file_returns_empty_card(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    card = load_card("inesistente")
    assert isinstance(card, CharacterCard)


# ── list_cards ────────────────────────────────────────────────────────────────


def test_list_cards_empty_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    result = list_cards()
    assert result == []


def test_list_cards_returns_one_entry(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "aurora.draft.yaml").write_text(
        yaml.dump({"name": "Aurora"}), encoding="utf-8"
    )
    result = list_cards()
    assert len(result) == 1
    assert result[0]["stem"] == "aurora"
    assert result[0]["name"] == "Aurora"


def test_list_cards_sorted_by_name(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    for name, stem in [("Zara", "zara"), ("Aurora", "aurora"), ("Mao", "mao")]:
        (tmp_path / f"{stem}.draft.yaml").write_text(yaml.dump({"name": name}), encoding="utf-8")
    result = list_cards()
    names = [r["name"] for r in result]
    assert names == sorted(names, key=str.lower)


def test_list_cards_has_compact_field(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "koko.draft.yaml").write_text(
        yaml.dump({"name": "Koko", "traits": ["vivace"]}), encoding="utf-8"
    )
    result = list_cards()
    assert "compact" in result[0]


# ── get_card_v3 / export_card_v3 ─────────────────────────────────────────────


def test_get_card_v3_returns_none_for_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    assert get_card_v3("nonexistent") is None


def test_get_card_v3_returns_dict(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "tingyun.draft.yaml").write_text(
        yaml.dump({"name": "Tingyun", "backstory": "mercante"}), encoding="utf-8"
    )
    d = get_card_v3("tingyun")
    assert isinstance(d, dict)
    assert d["name"] == "Tingyun"


def test_export_card_v3_alias(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "mao.draft.yaml").write_text(
        yaml.dump({"name": "Mao"}), encoding="utf-8"
    )
    assert get_card_v3("mao") == export_card_v3("mao")


# ── import_card_v3 ────────────────────────────────────────────────────────────


def test_import_card_v3_returns_character_card():
    d = {"name": "Aurora", "description": "guerriera", "extensions": {"calliope": {}}}
    card = import_card_v3(d)
    assert isinstance(card, CharacterCard)
    assert card.name == "Aurora"


def test_import_card_v3_preserves_extensions():
    d = {"name": "X", "extensions": {"calliope": {"speech_pattern": "arcaico"}}}
    card = import_card_v3(d)
    assert card.extensions["calliope"]["speech_pattern"] == "arcaico"


# ── resolve_character_sheet ──────────────────────────────────────────────────


def test_resolve_returns_dict_with_required_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    sheet = resolve_character_sheet("Unknown")
    for key in ("name", "traits", "backstory", "speech_pattern", "source"):
        assert key in sheet


def test_resolve_source_yaml_when_file_exists(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    (tmp_path / "aurora.draft.yaml").write_text(
        yaml.dump({"name": "Aurora", "backstory": "guerriera"}), encoding="utf-8"
    )
    sheet = resolve_character_sheet("Aurora")
    assert sheet["source"] == "yaml"
    assert "guerriera" in sheet["backstory"]


def test_resolve_source_none_for_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", str(tmp_path))
    sheet = resolve_character_sheet("Fantasma")
    assert sheet["source"] == "none"
