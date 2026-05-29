import pytest
from pathlib import Path

from app.calliope_shell.scene_model import (
    CharacterCard,
    SceneChat,
    load_character_yaml,
    load_scene_yaml,
)


@pytest.mark.unit
def test_v3_roundtrip_preserves_extensions():
    # Creiamo un dict con un campo extensions sconosciuto
    source_dict = {
        "name": "X",
        "description": "d",
        "extensions": {"foo": "bar"},
    }
    card = CharacterCard.from_v3_dict(source_dict)
    result_dict = card.to_v3_dict()

    # L'extensions deve essere preservato
    assert "extensions" in result_dict
    assert isinstance(result_dict["extensions"], dict)
    assert result_dict["extensions"]["foo"] == "bar"


@pytest.mark.unit
def test_compact_is_short():
    # Descrizione multilinea, ma compact deve usare solo la prima riga
    card = CharacterCard(
        name="Aria",
        description="riga1\nriga2 lunga molto",
    )
    compact = card.compact()
    # Deve contenere il nome
    assert "Aria" in compact
    # Non deve contenere la seconda riga della descrizione
    assert "riga2" not in compact
    # Deve essere più corto della descrizione completa
    assert len(compact) < len(card.description)

    # Con goal deve includere la stringa "goal: <goal>"
    compact_with_goal = card.compact(goal="vincere")
    assert "goal: vincere" in compact_with_goal


@pytest.mark.unit
def test_load_character_yaml_real():
    # Trova la radice del repository (come indicato nella specifica)
    repo_root = Path(__file__).resolve().parents[3]
    characters_dir = repo_root / "characters"
    yaml_files = list(characters_dir.glob("*.yaml"))

    if not yaml_files:
        pytest.skip("Nessun file YAML di character trovato nella directory legacy")

    # Carica il primo file YAML trovato
    card = load_character_yaml(yaml_files[0])

    # Verifiche di base
    assert isinstance(card, CharacterCard)
    assert isinstance(card.name, str)

    # Le chiavi non mappate devono finire in extensions
    assert isinstance(card.extensions, dict)


@pytest.mark.unit
def test_load_scene_yaml_readonly():
    # Trova la radice del repository (come indicato nella specifica)
    repo_root = Path(__file__).resolve().parents[3]
    scenes_dir = repo_root / "scenes"
    yaml_files = list(scenes_dir.glob("*.yaml"))

    if not yaml_files:
        pytest.skip("Nessun file YAML di scene trovato nella directory legacy")

    # Carica il primo file YAML trovato
    scene = load_scene_yaml(yaml_files[0])

    # Verifiche di base
    assert isinstance(scene, SceneChat)
    assert scene.read_only is True
    assert isinstance(scene.name, str)
