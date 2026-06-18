"""GAP-31: test unitari per scene_model.CharacterCard — compact, to_v3_dict, from_v3_dict, from_legacy_yaml."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.calliope_shell.scene_model import CharacterCard


def _card(**kwargs) -> CharacterCard:
    defaults = {"name": "Aria"}
    defaults.update(kwargs)
    return CharacterCard(**defaults)


# --- compact ----------------------------------------------------------------


def test_compact_uses_personality_first():
    card = _card(name="Aria", personality="brusca guerriera", description="descrizione lunga")
    result = card.compact()
    assert "brusca guerriera" in result
    assert "descrizione lunga" not in result


def test_compact_falls_back_to_description():
    card = _card(name="Mao", description="mago antico")
    result = card.compact()
    assert "mago antico" in result


def test_compact_includes_name():
    card = _card(name="Tingyun", personality="mercante")
    result = card.compact()
    assert "Tingyun" in result


def test_compact_first_line_only():
    card = _card(name="X", personality="linea uno\nlinea due\nlinea tre")
    result = card.compact()
    assert "linea due" not in result
    assert "linea uno" in result


def test_compact_goal_appended():
    card = _card(name="Y", personality="stoica")
    result = card.compact(goal="trovare il reliquiario")
    assert "goal: trovare il reliquiario" in result


def test_compact_no_goal_no_pipe():
    card = _card(name="Z", personality="impulsiva")
    result = card.compact()
    assert "|" not in result


# --- to_v3_dict / from_v3_dict round-trip -----------------------------------


def test_to_v3_dict_contains_name():
    card = _card(name="Aurora", description="guerriera")
    d = card.to_v3_dict()
    assert d["name"] == "Aurora"
    assert d["description"] == "guerriera"


def test_to_v3_dict_preserves_extensions():
    card = _card(name="A", extensions={"calliope": {"speech_pattern": "arcaico"}})
    d = card.to_v3_dict()
    assert d["extensions"]["calliope"]["speech_pattern"] == "arcaico"


def test_to_v3_dict_no_extensions_key_when_empty():
    card = _card(name="B")
    d = card.to_v3_dict()
    assert "extensions" not in d


def test_from_v3_dict_round_trip():
    original = CharacterCard(
        name="Koko",
        description="artista",
        personality="vivace",
        scenario="festival",
        extensions={"calliope": {"mood": "gioiosa"}},
    )
    d = original.to_v3_dict()
    restored = CharacterCard.from_v3_dict(d)
    assert restored.name == "Koko"
    assert restored.personality == "vivace"
    assert restored.extensions["calliope"]["mood"] == "gioiosa"


def test_from_v3_dict_missing_fields_default_empty():
    card = CharacterCard.from_v3_dict({"name": "Min"})
    assert card.description == ""
    assert card.extensions == {}


# --- from_legacy_yaml -------------------------------------------------------


def test_from_legacy_yaml_backstory_maps_to_description():
    card = CharacterCard.from_legacy_yaml({"name": "Aria", "backstory": "antica guerriera"})
    assert card.description == "antica guerriera"


def test_from_legacy_yaml_traits_list_to_personality():
    card = CharacterCard.from_legacy_yaml({"name": "Aria", "traits": ["coraggiosa", "leale"]})
    assert "coraggiosa" in card.personality
    assert "leale" in card.personality


def test_from_legacy_yaml_sample_quotes_to_mes_example():
    card = CharacterCard.from_legacy_yaml({
        "name": "Aria",
        "sample_quotes": ["Eccomi pronta.", "Non mi fermo mai."],
    })
    assert card.mes_example == "Eccomi pronta."


def test_from_legacy_yaml_unknown_keys_in_extensions():
    card = CharacterCard.from_legacy_yaml({
        "name": "X",
        "speech_pattern": {"tone": "brusco"},
        "custom_flag": True,
    })
    assert "speech_pattern" in card.extensions or "custom_flag" in card.extensions
