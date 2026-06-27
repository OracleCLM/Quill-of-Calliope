import os
import re

import yaml
from pathlib import Path
from typing import Dict, List, Optional

from app.calliope_shell.scene_model import CharacterCard


def _chars_dir() -> Path:
    """
    Returns the absolute Path to the ``characters`` directory.

    Override via ``CALLIOPE_CHARS_DIR`` (usato da test/journey per isolare il
    filesystem). Default: directory ``characters`` alla repo-root.
    """
    env = os.getenv("CALLIOPE_CHARS_DIR")
    if env:
        return Path(env)
    # __file__ -> app/calliope_shell/characters_service.py ; parents[2] -> repo root
    return Path(__file__).parents[2] / "characters"


def _slugify(name: str) -> str:
    """Slug filesystem-safe da un nome personaggio."""
    s = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return s or "char"


def create_draft(name: str) -> str:
    """Crea un ``<stem>.draft.yaml`` minimale per un nuovo personaggio.

    Non sovrascrive file esistenti (suffissa ``-1``, ``-2`` …). Ritorna lo ``stem``.
    """
    d = _chars_dir()
    d.mkdir(parents=True, exist_ok=True)
    stem = _slugify(name)
    candidate = stem
    idx = 1
    while (d / f"{candidate}.draft.yaml").is_file() or (d / f"{candidate}.canon.yaml").is_file():
        candidate = f"{stem}-{idx}"
        idx += 1
    stem = candidate
    with (d / f"{stem}.draft.yaml").open("w", encoding="utf-8") as f:
        yaml.safe_dump({"name": name}, f, allow_unicode=True, sort_keys=False)
    return stem


def resolve_character_sheet(name: str, conn=None) -> Dict:
    """GAP-3: scheda CANONICA RICCA di un personaggio (per il retrieval del refine).

    Unifica le fonti-schede frammentate con una precedenza unica:
    1. YAML draft/canon (card V3, la più ricca/strutturata) per stem = slug(name);
    2. tabella ``character_sheets`` (``content``) per character_name, se ``conn`` fornito;
    3. fallback name-only.

    Returns:
        dict con ``name, traits (list), backstory (str), speech_pattern (dict), source``.
    """
    sheet: Dict = {
        "name": name, "traits": [], "backstory": "", "speech_pattern": {}, "source": "none",
    }
    card = get_card_v3(_slugify(name))
    if card:
        pers = card.get("personality") or ""
        if isinstance(pers, str):
            traits = [t.strip() for t in pers.split(",") if t.strip()]
        else:
            traits = [str(t) for t in (pers or [])]
        example = (card.get("mes_example") or "").strip()
        sheet.update({
            "traits": traits,
            "backstory": (card.get("description") or "").strip()[:600],
            "speech_pattern": {"esempio": example[:300]} if example else {},
            "source": "yaml",
        })
        return sheet
    if conn is not None:
        try:
            row = conn.execute(
                "SELECT content FROM character_sheets WHERE character_name=? "
                "ORDER BY position_order LIMIT 1",
                (name,),
            ).fetchone()
        except Exception:
            row = None
        if row and (row[0] or ""):
            sheet.update({"backstory": str(row[0]).strip()[:600], "source": "character_sheets"})
            return sheet
    return sheet


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
