"""Unit test per scripts/build_lore_index.py — _extract_char_lore e _extract_scene_lore."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
import yaml

from scripts.build_lore_index import _extract_char_lore, _extract_scene_lore, build, main


# ── _extract_char_lore ────────────────────────────────────────────────────────

def test_char_invalid_yaml(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text("name: [invalid", encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_non_dict_yaml(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text("- item1\n- item2", encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_minimal_data_no_docs(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text(yaml.dump({"name": "Bob"}), encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_short_backstory_skipped(tmp_path):
    p = tmp_path / "char.yaml"
    p.write_text(yaml.dump({"name": "Bob", "backstory": "Short"}), encoding="utf-8")
    assert _extract_char_lore(p) == []


def test_char_long_backstory(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "backstory": "She was born in a forest and lived there for many years."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_backstory_alice"
    assert result[0]["text"] == "Alice — backstory: She was born in a forest and lived there for many years."
    assert result[0]["meta"]["type"] == "backstory"


def test_char_identity_basic(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "race": "Elf", "class": "Mage", "gender": "Female"}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_identity_alice"
    assert result[0]["text"] == "Alice is a Female Elf Mage"


def test_char_identity_with_details(tmp_path):
    p = tmp_path / "char.yaml"
    data = {
        "name": "Alice", "race": "Human", "class": "Warrior", "gender": "Male",
        "origin": "London", "age": "30",
        "traits": ["Brave", "Strong", "Loud", "Fast", "Smart", "Wise"],
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    text = result[0]["text"]
    assert "Alice is a Male Human Warrior" in text
    assert "from London" in text
    assert "age 30" in text
    assert "Traits: Brave, Strong, Loud, Fast, Smart" in text
    assert "Wise" not in text  # solo 5 traits


def test_char_relationships(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "relationships": {"Bob": "Friend", "Charlie": "Enemy"}}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_rels_alice"
    assert "Alice relationships:" in result[0]["text"]
    assert "Bob: Friend" in result[0]["text"]


def test_char_behavior_role(tmp_path):
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "behavior_pattern": {"role": "Leader"}}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "char_role_alice"


def test_char_combined_docs(tmp_path):
    p = tmp_path / "char.yaml"
    data = {
        "name": "Alice",
        "backstory": "She was born in a forest and lived there for many years.",
        "race": "Elf", "class": "Ranger", "gender": "Female",
        "relationships": {"Bob": "Ally"},
        "behavior_pattern": {"role": "Scout"},
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert len(result) == 4
    ids = {doc["id"] for doc in result}
    assert "char_backstory_alice" in ids
    assert "char_identity_alice" in ids
    assert "char_rels_alice" in ids
    assert "char_role_alice" in ids


# ── _extract_scene_lore ───────────────────────────────────────────────────────

def test_scene_invalid_yaml(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text("title: [invalid", encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_non_dict_yaml(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump(["list", "item"]), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_missing_summary(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump({"title": "Event"}), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_short_summary_skipped(tmp_path):
    p = tmp_path / "scene.yaml"
    p.write_text(yaml.dump({"title": "Event", "summary": "Short"}), encoding="utf-8")
    assert _extract_scene_lore(p) == []


def test_scene_valid_basic(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"title": "The Battle", "summary": "A great battle took place at dawn."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "scene_lore_scene"
    assert result[0]["text"] == "Scene 'The Battle': A great battle took place at dawn."
    assert result[0]["meta"]["source"] == "scene"
    assert result[0]["meta"]["type"] == "event"


def test_scene_with_participants(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {
        "title": "The Meeting",
        "summary": "They discussed the future of the realm in great detail.",
        "participants": ["Alice", "Bob"],
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert "(participants: Alice, Bob)" in result[0]["text"]
    assert result[0]["meta"]["participants"] == "Alice,Bob"


def test_scene_long_text_truncated(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"title": "Long Event", "summary": "x" * 600}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert len(result[0]["text"]) == 500


def test_scene_custom_id(tmp_path):
    p = tmp_path / "scene.yaml"
    data = {"scene_id": "act1_scene1", "title": "Start", "summary": "The story begins here for real."}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_scene_lore(p)
    assert len(result) == 1
    assert result[0]["id"] == "scene_lore_act1_scene1"
    assert result[0]["meta"]["scene_id"] == "act1_scene1"


# ── _extract_char_lore: lines 80, 83 ─────────────────────────────────────────

def test_char_behavior_with_decision_style(tmp_path):
    """Line 80: decision_style presente → aggiunto al testo."""
    p = tmp_path / "char.yaml"
    data = {"name": "Alice", "behavior_pattern": {"role": "Leader", "decision_style": "calcolo freddo"}}
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert any("calcolo freddo" in d["text"] for d in result)


def test_char_behavior_with_typical_actions(tmp_path):
    """Line 83: typical_actions non vuoto → azioni aggiunte al testo."""
    p = tmp_path / "char.yaml"
    data = {
        "name": "Alice",
        "behavior_pattern": {"role": "Scout", "typical_actions": ["patrol", "observe", "report"]},
    }
    p.write_text(yaml.dump(data), encoding="utf-8")
    result = _extract_char_lore(p)
    assert any("patrol" in d["text"] for d in result)


# ── build() e main() ──────────────────────────────────────────────────────────

def _mock_chroma_client():
    col = MagicMock()
    col.count.return_value = 0
    client = MagicMock()
    client.get_or_create_collection.return_value = col
    return client, col


def test_build_no_docs_returns_0(tmp_path):
    """Lines 126-160: nessun doc → stampa messaggio e ritorna 0."""
    client, _ = _mock_chroma_client()
    with patch("chromadb.PersistentClient", return_value=client), \
         patch("scripts.build_lore_index._CHARS_DIR", tmp_path), \
         patch("scripts.build_lore_index._SCENES_DIR", tmp_path):
        result = build()
    assert result == 0


def test_build_with_docs_calls_upsert(tmp_path):
    """Lines 126-160: doc trovati → upsert chiamato, ritorna count."""
    chars_dir = tmp_path / "chars"
    chars_dir.mkdir()
    char_data = {
        "name": "Zora",
        "backstory": "Nacque in una terra lontana e visse molti anni nell'ombra.",
    }
    (chars_dir / "zora.yaml").write_text(yaml.dump(char_data), encoding="utf-8")

    client, col = _mock_chroma_client()
    with patch("chromadb.PersistentClient", return_value=client), \
         patch("scripts.build_lore_index._CHARS_DIR", chars_dir), \
         patch("scripts.build_lore_index._SCENES_DIR", tmp_path / "scenes"):
        result = build()
    assert result > 0
    assert col.upsert.called


def test_build_reset_deletes_collection(tmp_path):
    """Lines 129-132: reset=True → delete_collection chiamato."""
    client, col = _mock_chroma_client()
    with patch("chromadb.PersistentClient", return_value=client), \
         patch("scripts.build_lore_index._CHARS_DIR", tmp_path), \
         patch("scripts.build_lore_index._SCENES_DIR", tmp_path):
        build(reset=True)
    client.delete_collection.assert_called_once()


def test_build_reset_exception_continues(tmp_path):
    """Lines 131-132: delete_collection fallisce → build continua senza crash."""
    client, _ = _mock_chroma_client()
    client.delete_collection.side_effect = Exception("not found")
    with patch("chromadb.PersistentClient", return_value=client), \
         patch("scripts.build_lore_index._CHARS_DIR", tmp_path), \
         patch("scripts.build_lore_index._SCENES_DIR", tmp_path):
        result = build(reset=True)
    assert result == 0


def test_build_with_scene_docs(tmp_path):
    """Line 142: loop _SCENES_DIR eseguito quando ci sono scene yaml."""
    scenes_dir = tmp_path / "scenes"
    scenes_dir.mkdir()
    scene_data = {
        "scene_id": "s01", "title": "La Battaglia",
        "summary": "Una battaglia epica che cambia per sempre il destino degli eroi.",
        "participants": ["Alice", "Bob"],
    }
    (scenes_dir / "scene01.yaml").write_text(yaml.dump(scene_data), encoding="utf-8")

    client, col = _mock_chroma_client()
    with patch("chromadb.PersistentClient", return_value=client), \
         patch("scripts.build_lore_index._CHARS_DIR", tmp_path / "chars"), \
         patch("scripts.build_lore_index._SCENES_DIR", scenes_dir):
        result = build()
    assert result > 0
    assert col.upsert.called


def test_main_exits_0_when_docs_found(tmp_path, monkeypatch):
    """Lines 164-168: build() ritorna >0 → sys.exit(0)."""
    monkeypatch.setattr("sys.argv", ["build_lore_index.py"])
    with patch("scripts.build_lore_index.build", return_value=5):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 0


def test_main_exits_1_when_no_docs(tmp_path, monkeypatch):
    """Lines 164-168: build() ritorna 0 → sys.exit(1)."""
    monkeypatch.setattr("sys.argv", ["build_lore_index.py"])
    with patch("scripts.build_lore_index.build", return_value=0):
        with pytest.raises(SystemExit) as exc:
            main()
    assert exc.value.code == 1
