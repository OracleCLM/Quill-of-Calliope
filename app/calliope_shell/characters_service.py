import yaml
from pathlib import Path
from typing import Dict, List, Optional

from app.calliope_shell.scene_model import CharacterCard


def _chars_dir() -> Path:
    """
    Returns the absolute Path to the repository's top‑level ``characters`` directory.
    """
    # __file__ -> app/calliope_shell/characters_service.py
    # parents[2] -> repository root
    return Path(__file__).parents[2] / "characters"


def _merged_legacy_dict(stem: str) -> Dict:
    """
    Load the ``<stem>.draft.yaml`` (if present) and, if a ``<stem>.canon.yaml`` exists,
    apply its ``overrides`` on top of the draft data (shallow merge, overrides win).
    Returns the resulting dictionary – possibly empty if neither file exists.
    """
    base: Dict = {}
    draft_path = _chars_dir() / f"{stem}.draft.yaml"
    if draft_path.is_file():
        try:
            with draft_path.open("r", encoding="utf-8") as f:
                base = yaml.safe_load(f) or {}
        except Exception:
            # YAML malformato o errore di I/O: trattiamo come dizionario vuoto
            base = {}

    canon_path = _chars_dir() / f"{stem}.canon.yaml"
    if canon_path.is_file():
        try:
            with canon_path.open("r", encoding="utf-8") as f:
                canon_data = yaml.safe_load(f) or {}
        except Exception:
            # YAML malformato o errore di I/O: ignoriamo gli overrides
            canon_data = {}
        overrides = canon_data.get("overrides", {})
        if isinstance(overrides, dict):
            # Shallow merge – overrides win
            base.update(overrides)

    return base


def load_card(stem: str) -> CharacterCard:
    """
    Load a character card identified by ``stem`` (e.g. ``arianna``) applying any
    canon overrides, and convert it to a ``CharacterCard`` instance.
    """
    merged = _merged_legacy_dict(stem)
    return CharacterCard.from_legacy_yaml(merged)


def list_cards() -> List[Dict]:
    """
    Returns a list of compact dictionaries for every character card found in the
    repository.  The list is sorted alphabetically by the character's ``name``.
    Each dict contains:
        - stem: the identifier (filename without suffixes)
        - name: the character's name
        - compact: the compact representation (``card.compact()``)
        - tags: the list of tags (may be empty)
    """
    chars_path = _chars_dir()
    stems = set()

    # Collect stems from *.draft.yaml
    for p in chars_path.glob("*.draft.yaml"):
        stem = p.name[:-len(".draft.yaml")]
        stems.add(stem)

    # Also collect stems that have only a canon file (no draft)
    for p in chars_path.glob("*.canon.yaml"):
        stem = p.name[:-len(".canon.yaml")]
        stems.add(stem)

    result = []
    for stem in stems:
        try:
            card = load_card(stem)
            result.append(
                {
                    "stem": stem,
                    "name": card.name,
                    "compact": card.compact(),
                    "tags": card.tags,
                }
            )
        except Exception:
            # Se il caricamento della card fallisce (YAML corrotto, ecc.), la saltiamo
            continue

    # Sort by name (case‑insensitive)
    result.sort(key=lambda x: x["name"].lower())
    return result


def get_card_v3(stem: str) -> Optional[Dict]:
    """
    Returns the full V3 dictionary representation of the character card,
    preserving any ``extensions``.  If the card does not exist, returns ``None``.
    """
    chars_path = _chars_dir()
    draft_exists = (chars_path / f"{stem}.draft.yaml").is_file()
    canon_exists = (chars_path / f"{stem}.canon.yaml").is_file()
    if not (draft_exists or canon_exists):
        return None

    try:
        card = load_card(stem)
        return card.to_v3_dict()
    except Exception:
        # YAML malformato o altro errore: restituiamo None
        return None


def export_card_v3(stem: str) -> Optional[Dict]:
    """
    Alias for ``get_card_v3`` – kept for semantic clarity (exporting a V3 card).
    """
    return get_card_v3(stem)


def import_card_v3(data: Dict) -> CharacterCard:
    """
    Constructs a ``CharacterCard`` from a V3 dictionary (round‑trip preserving
    extensions).  Returns the ``CharacterCard`` instance.
    """
    return CharacterCard.from_v3_dict(data)
