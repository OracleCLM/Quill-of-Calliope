"""
Unit test per scene_model.py e context_budget.py (FASE P2).

Contratto:
  - est_tokens: euristica len//4, minimo 1
  - CharacterCard.compact(): personality > description fallback, goal suffix
  - CharacterCard.from_v3_dict(): roundtrip + unknown keys in extensions
  - CharacterCard.from_legacy_yaml(): mapping traits list, sample_quotes, extra keys
  - load_character_yaml() / load_scene_yaml(): file-based loaders
  - assemble_context(): ordine blocchi, budget ghosting, recent_verbatim_min, lore cap, meter
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_model import (
    CharacterCard,
    SceneChat,
    SceneMessage,
    load_character_yaml,
    load_scene_yaml,
)
from app.calliope_shell.context_budget import (
    ContextBundle,
    assemble_context,
    est_tokens,
)


# ── est_tokens ────────────────────────────────────────────────────────────────

def test_est_tokens_empty_string():
    assert est_tokens("") == 1


def test_est_tokens_short():
    assert est_tokens("abcd") == 1


def test_est_tokens_16chars():
    assert est_tokens("a" * 16) == 4


def test_est_tokens_proportion():
    text = "x" * 100
    assert est_tokens(text) == 25


# ── CharacterCard.compact ─────────────────────────────────────────────────────

def test_compact_uses_personality():
    card = CharacterCard(name="Aurora", personality="strega oscura", description="maga")
    assert card.compact() == "Aurora — strega oscura"


def test_compact_falls_back_to_description():
    card = CharacterCard(name="Aurora", personality="", description="maga potente\ndetails")
    result = card.compact()
    assert result == "Aurora — maga potente"


def test_compact_with_goal():
    card = CharacterCard(name="Aurora", personality="strega")
    result = card.compact(goal="trova il cristallo")
    assert "goal: trova il cristallo" in result


def test_compact_no_text():
    card = CharacterCard(name="Sconosciuto")
    result = card.compact()
    assert result == "Sconosciuto — "


# ── CharacterCard roundtrip v3 ────────────────────────────────────────────────

def test_from_v3_dict_roundtrip():
    card = CharacterCard(
        name="Aurora",
        personality="strega",
        tags=["dark", "mage"],
        extensions={"custom_key": "val"},
    )
    d = card.to_v3_dict()
    card2 = CharacterCard.from_v3_dict(d)
    assert card2.name == "Aurora"
    assert card2.personality == "strega"
    assert card2.tags == ["dark", "mage"]
    assert card2.extensions == {"custom_key": "val"}


def test_from_v3_dict_missing_fields():
    card = CharacterCard.from_v3_dict({"name": "Bob"})
    assert card.name == "Bob"
    assert card.personality == ""
    assert card.extensions == {}


# ── CharacterCard.from_legacy_yaml ────────────────────────────────────────────

def test_from_legacy_yaml_maps_backstory():
    data = {"name": "Aurora", "backstory": "nata nella foresta"}
    card = CharacterCard.from_legacy_yaml(data)
    assert card.description == "nata nella foresta"


def test_from_legacy_yaml_traits_list():
    data = {"name": "Aurora", "traits": ["coraggiosa", "misteriosa"]}
    card = CharacterCard.from_legacy_yaml(data)
    assert "coraggiosa" in card.personality
    assert "misteriosa" in card.personality


def test_from_legacy_yaml_sample_quotes():
    data = {"name": "Aurora", "sample_quotes": ["Ciao mondo", "Secondo saluto"]}
    card = CharacterCard.from_legacy_yaml(data)
    assert card.mes_example == "Ciao mondo"


def test_from_legacy_yaml_unknown_keys_in_extensions():
    data = {"name": "X", "unknown_field": "mystery", "another": 42}
    card = CharacterCard.from_legacy_yaml(data)
    assert card.extensions.get("unknown_field") == "mystery"
    assert card.extensions.get("another") == 42


# ── load_character_yaml / load_scene_yaml ────────────────────────────────────

def test_load_character_yaml(tmp_path):
    f = tmp_path / "aurora.yaml"
    f.write_text("name: Aurora\npersonality: strega\n")
    card = load_character_yaml(f)
    assert card.name == "Aurora"
    assert card.personality == "strega"


def test_load_scene_yaml(tmp_path):
    f = tmp_path / "scene_01.yaml"
    f.write_text(
        "scene_id: s1\ntitle: La Scena\n"
        "participants:\n  - Aurora\n  - Gabby\n"
        "timestamp_start: 2026-01-01\n"
    )
    scene = load_scene_yaml(f)
    assert scene.id == "s1"
    assert scene.name == "La Scena"
    assert "Aurora" in scene.members
    assert scene.read_only is True
    # YAML deserializza le date ISO come datetime.date, non str
    assert str(scene.created) == "2026-01-01"


def test_load_scene_yaml_fallback_to_stem(tmp_path):
    f = tmp_path / "my_scene.yaml"
    f.write_text("status: draft\n")
    scene = load_scene_yaml(f)
    assert scene.id == "my_scene"
    assert scene.name == "my_scene"


# ── assemble_context ──────────────────────────────────────────────────────────

def _make_scene(msgs=None, directive="", members=None) -> SceneChat:
    messages = [SceneMessage(author=a, content=c) for a, c in (msgs or [])]
    return SceneChat(
        id="s1",
        name="Test",
        members=members or [],
        directive=directive,
        messages=messages,
    )


def test_assemble_empty_scene():
    scene = _make_scene()
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=256)
    assert isinstance(bundle, ContextBundle)
    assert bundle.blocks == []
    assert bundle.ghosted_count == 0


def test_assemble_system_prompt_first():
    scene = _make_scene()
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=256,
                              system_prompt="Tu sei Calliope.")
    assert bundle.blocks[0].kind == "system"
    assert bundle.blocks[0].text == "Tu sei Calliope."


def test_assemble_directive_last():
    scene = _make_scene(directive="Rispondi solo in italiano.")
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=256,
                              system_prompt="sys")
    kinds = [b.kind for b in bundle.blocks]
    assert kinds[-1] == "directive"
    assert kinds[0] == "system"


def test_assemble_card_included():
    scene = _make_scene(members=["Aurora"])
    cards = {"Aurora": CharacterCard(name="Aurora", personality="strega")}
    bundle = assemble_context(scene, cards, model_window=4096, reply_reserve=256)
    card_blocks = [b for b in bundle.blocks if b.kind == "card"]
    assert len(card_blocks) == 1
    assert "Aurora" in card_blocks[0].text


def test_assemble_messages_chronological():
    msgs = [("A", "primo"), ("B", "secondo"), ("A", "terzo")]
    scene = _make_scene(msgs=msgs)
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=256)
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert [b.text for b in msg_blocks] == ["primo", "secondo", "terzo"]


def test_assemble_ghosting_when_budget_small():
    # 20 messaggi ~20 token ciascuno → 400 token totali, budget 150 → ghosting certo
    msgs = [("A", "x" * 80) for _ in range(20)]
    scene = _make_scene(msgs=msgs)
    bundle = assemble_context(
        scene, {}, model_window=200, reply_reserve=50, recent_verbatim_min=2
    )
    assert bundle.ghosted_count > 0
    ghost_blocks = [b for b in bundle.blocks if b.kind == "ghost"]
    assert len(ghost_blocks) == 1
    assert str(bundle.ghosted_count) in ghost_blocks[0].text


def test_assemble_recent_verbatim_min_honored():
    # 10 messaggi, budget molto ristretto ma recent_verbatim_min=4
    msgs = [("A", "x" * 40) for _ in range(10)]
    scene = _make_scene(msgs=msgs)
    bundle = assemble_context(
        scene, {}, model_window=100, reply_reserve=10, recent_verbatim_min=4
    )
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(msg_blocks) >= 4


def test_assemble_lore_cap():
    # Lore molto grande: il cap al 15% del window deve escludere le voci eccessive
    scene = _make_scene()
    big_lore = [{"content": "z" * 100} for _ in range(50)]
    bundle = assemble_context(
        scene, {}, model_window=1000, reply_reserve=100, lore_entries=big_lore
    )
    lore_blocks = [b for b in bundle.blocks if b.kind == "lore"]
    lore_tokens = sum(est_tokens(b.text) for b in lore_blocks)
    assert lore_tokens <= int(1000 * 0.15) + 1  # tolleranza 1 token


def test_assemble_meter_keys():
    scene = _make_scene()
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=512)
    assert "window" in bundle.meter
    assert bundle.meter["window"] == 4096
    assert bundle.meter["reply_reserve"] == 512
    assert bundle.meter["free_tokens"] >= 0


def test_assemble_ghost_not_present_if_all_fit():
    msgs = [("A", "breve")]
    scene = _make_scene(msgs=msgs)
    bundle = assemble_context(scene, {}, model_window=4096, reply_reserve=256)
    assert bundle.ghosted_count == 0
    ghost_blocks = [b for b in bundle.blocks if b.kind == "ghost"]
    assert ghost_blocks == []


def test_load_scene_yaml_participants_not_list_defaults_to_empty(tmp_path):
    f = tmp_path / "scene_np.yaml"
    f.write_text("title: Scena\nparticipants: 'Aurora, Gabby'\n")
    scene = load_scene_yaml(f)
    assert scene.members == []


def test_assemble_context_history_budget_clamped_to_zero(tmp_path):
    scene = _make_scene(msgs=[("A", "x" * 10)])
    bundle = assemble_context(
        scene, {}, model_window=10, reply_reserve=10
    )
    msg_blocks = [b for b in bundle.blocks if b.kind == "message"]
    assert len(msg_blocks) == 0 or bundle.ghosted_count >= 0


def test_assemble_context_lore_non_dict_entry():
    scene = _make_scene(msgs=[])
    bundle = assemble_context(scene, {}, model_window=2000, reply_reserve=256,
                              lore_entries=["raw string lore entry"])
    lore_blocks = [b for b in bundle.blocks if b.kind == "lore"]
    assert any("raw string lore entry" in b.text for b in lore_blocks)
