# -*- coding: utf-8 -*-
"""
Lore Knowledge Base (editable per topic) – backend semplificato.

Questo modulo fornisce:
- Costanti delle categorie di lore.
- Dataclass ``LoreEntry`` con metodi di serializzazione.
- Classe ``LoreStore`` per la persistenza JSON e operazioni CRUD.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

# --------------------------------------------------------------------------- #
# 1) Categorie di lore – costanti di modulo
# --------------------------------------------------------------------------- #
WORLD_SETTING = "world_setting"
PLACES = "places"
CHARACTERS_EVENTS = "characters_events"
MECHANICS_MAGIC = "mechanics_magic"
OTHER = "other"

LORE_CATEGORIES: List[str] = [
    WORLD_SETTING,
    PLACES,
    CHARACTERS_EVENTS,
    MECHANICS_MAGIC,
    OTHER,
]

# --------------------------------------------------------------------------- #
# 2) Dataclass LoreEntry (stile V3 character_book)
# --------------------------------------------------------------------------- #
def _validate_category(cat: str) -> str:
    """Restituisce la categoria valida, oppure ``OTHER``."""
    return cat if cat in LORE_CATEGORIES else OTHER


@dataclass
class LoreEntry:
    id: str
    title: str
    category: str = OTHER
    keys: List[str] = field(default_factory=list)
    content: str = ""
    insertion_order: int = 100
    scope: str = "global"  # "global" | "character" | "scene"
    constant: bool = False
    extensions: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalizza la categoria
        self.category = _validate_category(self.category)

    # --------------------------------------------------------------------- #
    # Serializzazione / deserializzazione
    # --------------------------------------------------------------------- #
    def to_dict(self) -> Dict[str, Any]:
        """Ritorna una rappresentazione JSON‑serializzabile dell'entry."""
        data: Dict[str, Any] = {
            "id": self.id,
            "title": self.title,
            "category": _validate_category(self.category),
            "keys": list(self.keys),
            "content": self.content,
            "insertion_order": self.insertion_order,
            "scope": self.scope,
            "constant": self.constant,
        }
        if self.extensions:
            data["extensions"] = dict(self.extensions)
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoreEntry":
        """Crea un'istanza da un dizionario, preservando le estensioni."""
        extensions = data.get("extensions", {})
        # Rimuoviamo le chiavi note per evitare conflitti con **kwargs
        known = {
            "id",
            "title",
            "category",
            "keys",
            "content",
            "insertion_order",
            "scope",
            "constant",
        }
        init_kwargs = {k: data.get(k) for k in known}
        # Assicuriamoci che i tipi siano corretti
        init_kwargs["keys"] = list(init_kwargs.get("keys") or [])
        init_kwargs["extensions"] = dict(extensions)
        return cls(**init_kwargs)  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# 3) Classe LoreStore – gestione della persistenza JSON
# --------------------------------------------------------------------------- #
def _default_store_path() -> Path:
    """Percorso di default: <repo_root>/data/lore_kb.json."""
    # Il file si trova due livelli sopra di questo modulo (repo root)
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "data" / "lore_kb.json"


def _slugify(text: str) -> str:
    """Crea uno slug semplice da un titolo."""
    text = text.lower()
    # Sostituisce tutti i caratteri non alfanumerici con trattini
    text = re.sub(r"[^a-z0-9]+", "-", text)
    # Rimuove trattini iniziali/finali
    return text.strip("-")


class LoreStore:
    def __init__(self, path: Optional[Path] = None) -> None:
        """
        Inizializza il negozio.

        Se ``path`` è fornito (anche come stringa), lo converte in ``Path``.
        Altrimenti utilizza il percorso di default.
        """
        if path is None:
            self.path: Path = _default_store_path()
        else:
            # Accetta sia stringhe che oggetti Path
            self.path = Path(path) if not isinstance(path, Path) else path

        self._entries: List[LoreEntry] = []
        self.load()

    # --------------------------------------------------------------------- #
    # Caricamento / salvataggio
    # --------------------------------------------------------------------- #
    def load(self) -> None:
        """Carica la lista di entry dal file JSON. In caso di errore, usa [] ."""
        if not self.path.is_file():
            self._entries = []
            return

        try:
            with self.path.open("r", encoding="utf-8") as f:
                raw = json.load(f) or []
        except (json.JSONDecodeError, OSError):
            self._entries = []
            return

        if not isinstance(raw, list):
            self._entries = []
            return

        self._entries = [LoreEntry.from_dict(item) for item in raw if isinstance(item, dict)]

    def save(self) -> None:
        """Scrive la lista di entry in modo atomico (tmp + rename)."""
        # Assicura che la directory di destinazione esista
        self.path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self.path.with_suffix(".tmp")
        data = [entry.to_dict() for entry in self._entries]

        try:
            with tmp_path.open("w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            tmp_path.replace(self.path)
        finally:
            # Pulizia in caso di errore di scrittura
            if tmp_path.is_file():
                try:
                    tmp_path.unlink()
                except OSError:
                    pass

    # --------------------------------------------------------------------- #
    # Operazioni CRUD
    # --------------------------------------------------------------------- #
    def _generate_unique_id(self, title: str) -> str:
        """Genera un id unico basato sullo slug del titolo."""
        base = _slugify(title) or "entry"
        candidate = base
        idx = 1
        existing_ids = {e.id for e in self._entries}
        while candidate in existing_ids:
            candidate = f"{base}-{idx}"
            idx += 1
        return candidate

    def add_entry(self, entry: LoreEntry) -> LoreEntry:
        """Aggiunge una nuova entry (generando id se necessario) e salva."""
        if not entry.id:
            entry.id = self._generate_unique_id(entry.title)

        # Se l'id è già presente, lo sovrascriviamo (comportamento esplicito)
        self._entries = [e for e in self._entries if e.id != entry.id]
        # Inserimento ordine: se non specificato, usa max+1
        if entry.insertion_order == 100:
            max_order = max((e.insertion_order for e in self._entries), default=0)
            entry.insertion_order = max_order + 1

        self._entries.append(entry)
        self.save()
        return entry

    def update_entry(self, entry_id: str, **fields: Any) -> Optional[LoreEntry]:
        """Aggiorna i campi di una entry esistente; ritorna l'entry aggiornata o None."""
        entry = self.get_entry(entry_id)
        if entry is None:
            return None

        for key, value in fields.items():
            if not hasattr(entry, key):
                # Ignora campi sconosciuti (potrebbero essere destinati a extensions)
                continue
            if key == "category":
                setattr(entry, key, _validate_category(value))
            else:
                setattr(entry, key, value)

        self.save()
        return entry

    def delete_entry(self, entry_id: str) -> bool:
        """Rimuove l'entry con l'id specificato; ritorna True se trovata."""
        original_len = len(self._entries)
        self._entries = [e for e in self._entries if e.id != entry_id]
        if len(self._entries) != original_len:
            self.save()
            return True
        return False

    def get_entry(self, entry_id: str) -> Optional[LoreEntry]:
        """Restituisce l'entry corrispondente o None."""
        for entry in self._entries:
            if entry.id == entry_id:
                return entry
        return None

    # --------------------------------------------------------------------- #
    # Query
    # --------------------------------------------------------------------- #
    def list_by_category(self, category: Optional[str] = None) -> List[LoreEntry]:
        """Ritorna tutte le entry, eventualmente filtrate per categoria,
        ordinate per ``insertion_order`` e poi per ``title``."""
        filtered = (
            [e for e in self._entries if e.category == category]
            if category
            else list(self._entries)
        )
        filtered.sort(key=lambda e: (e.insertion_order, e.title.lower()))
        return filtered

    def triggered_entries(self, text: str, max_entries: int = 20) -> List[LoreEntry]:
        """
        Restituisce le entry da utilizzare per il sub‑budget di P2.

        - Prima tutte le entry con ``constant == True`` (in ordine di insertion_order).
        - Poi le entry le cui ``keys`` compaiono nel testo (case‑insensitive,
          ricerca di sottostringhe).
        - Dedupe per ``id``.
        - Ordina: constant prima (descendente), poi insertion_order ascendente.
        - Limita a ``max_entries``.
        """
        lowered = text.lower()
        result: List[LoreEntry] = []
        seen_ids: set[str] = set()

        # 1) Costanti
        const_entries = [e for e in self._entries if e.constant]
        const_entries.sort(key=lambda e: e.insertion_order)
        for e in const_entries:
            if e.id not in seen_ids:
                result.append(e)
                seen_ids.add(e.id)

        # 2) Entry attivate dalle chiavi — whole-word match (case-insensitive).
        # Usa lookbehind/lookahead su \w per evitare falsi positivi da substring
        # (es. chiave "Ra" NON matcha "narrator"; "on" NON matcha "monster").
        non_const = [e for e in self._entries if not e.constant]
        for entry in non_const:
            for key in entry.keys:
                _k = key.lower()
                if re.search(r"(?<!\w)" + re.escape(_k) + r"(?!\w)", lowered):
                    if entry.id not in seen_ids:
                        result.append(entry)
                        seen_ids.add(entry.id)
                    break  # non serve controllare altre chiavi

        # Ordinamento finale
        result.sort(key=lambda e: (not e.constant, e.insertion_order))
        return result[:max_entries]
