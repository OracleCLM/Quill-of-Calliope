"""
Modulo di gestione dei personaggi per il database di Calliope.

Fornisce funzioni CRUD per la tabella ``characters`` e gestisce le
associazioni con le scene tramite ``scene_characters``.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Mapping, Optional

_UNSET = object()  # sentinel: distingue "non fornito" da None esplicito (es. cancella image_path)

# Importiamo utility generiche dal package ``app.db``.
try:
    from app.db import new_id  # type: ignore
except Exception:  # pragma: no cover
    # Fallback se new_id non è disponibile
    new_id = None  # type: ignore


def _row_to_dict(cursor: sqlite3.Cursor, row: tuple) -> dict:
    """Converte una riga del cursore in un dizionario."""
    cols = [desc[0] for desc in cursor.description]
    return dict(zip(cols, row))


def add_character(
    conn: sqlite3.Connection,
    *,
    name: str,
    kind: str = "npc",
    card_json: Optional[str] = None,
    image_path: Optional[str] = None,
) -> str:
    """
    Inserisce un nuovo personaggio.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    name:
        Nome del personaggio.
    kind:
        Tipo di personaggio (operator, player, npc).
    card_json:
        Dati JSON della scheda personaggio.
    image_path:
        Percorso dell'immagine del personaggio.

    Returns
    -------
    str
        L'ID del personaggio appena inserito.
    """
    if not name:
        raise ValueError("name non può essere vuoto")
    if len(name) > 255:
        raise ValueError("name non può superare 255 caratteri")
    if new_id is None:
        raise RuntimeError("new_id function not available")

    char_id = new_id()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO characters (id, name, kind, card_json, image_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (char_id, name, kind, card_json, image_path),
    )
    conn.commit()
    return char_id


def get_character(
    conn: sqlite3.Connection, character_id: str
) -> Optional[Mapping[str, object]]:
    """
    Recupera un personaggio per ID.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    character_id:
        ID del personaggio.

    Returns
    -------
    Optional[Mapping[str, object]]
        Dizionario con i dati del personaggio o None.
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT * FROM characters WHERE id = ?",
        (character_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(cur, row)


def list_characters(
    conn: sqlite3.Connection, kind: Optional[str] = None
) -> List[Mapping[str, object]]:
    """
    Elenca i personaggi, opzionalmente filtrati per tipo.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    kind:
        Se fornito, filtra solo questo tipo.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari rappresentanti i personaggi.
    """
    cur = conn.cursor()
    if kind:
        cur.execute(
            "SELECT * FROM characters WHERE kind = ?",
            (kind,),
        )
    else:
        cur.execute("SELECT * FROM characters")

    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def update_character(
    conn: sqlite3.Connection,
    character_id: str,
    *,
    name: Optional[str] = None,
    card_json: Optional[str] = None,
    image_path=_UNSET,
    kind: Optional[str] = None,
) -> bool:
    """
    Aggiorna un personaggio.

    Aggiorna solo i campi forniti (non None).

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    character_id:
        ID del personaggio.
    name:
        Nuovo nome.
    card_json:
        Nuovi dati JSON.
    image_path:
        Nuovo percorso immagine.
    kind:
        Nuovo tipo.

    Returns
    -------
    bool
        True se il personaggio esisteva ed è stato aggiornato.
    """
    check_cur = conn.cursor()
    check_cur.execute("SELECT 1 FROM characters WHERE id = ?", (character_id,))
    exists = check_cur.fetchone() is not None

    if not exists:
        return False

    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if card_json is not None:
        updates.append("card_json = ?")
        params.append(card_json)
    if image_path is not _UNSET:
        updates.append("image_path = ?")
        params.append(image_path)
    if kind is not None:
        updates.append("kind = ?")
        params.append(kind)

    if not updates:
        return True

    params.append(character_id)
    query = f"UPDATE characters SET {', '.join(updates)} WHERE id = ?"

    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    return True


def delete_character(
    conn: sqlite3.Connection, character_id: str
) -> bool:
    """
    Elimina un personaggio.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    character_id:
        ID del personaggio.

    Returns
    -------
    bool
        True se eliminato, False se non esisteva.
    """
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM characters WHERE id = ?",
        (character_id,),
    )
    conn.commit()
    return cur.rowcount > 0


# =========================================================================== #
# SSOT — Character Card V2 loader/saver (R-CALLIOPE-MA-CHAR-SSOT-MIGRATION)
# =========================================================================== #

CARD_V2_SPEC = "chara_card_v2"
CARD_V2_VERSION = "2.0"

# Campi-prompt canonici dello spec Character Card V2 (data.*)
_CARD_V2_DATA_STR_FIELDS = (
    "name",
    "description",
    "personality",
    "scenario",
    "first_mes",
    "mes_example",
    "system_prompt",
    "post_history_instructions",
    "creator_notes",
)
_CARD_V2_DATA_LIST_FIELDS = ("tags",)


def empty_card_v2(name: str = "") -> Dict[str, Any]:
    """Restituisce uno scheletro Card V2 vuoto (nessun campo inventato)."""
    return {
        "spec": CARD_V2_SPEC,
        "spec_version": CARD_V2_VERSION,
        "data": {
            "name": name,
            "description": "",
            "personality": "",
            "scenario": "",
            "first_mes": "",
            "mes_example": "",
            "system_prompt": "",
            "post_history_instructions": "",
            "creator_notes": "",
            "tags": [],
            "character_book": None,
            "extensions": {"calliope": {}},
        },
    }


def load_card_v2(conn: sqlite3.Connection, name: str) -> Optional[Dict[str, Any]]:
    """Carica la Card V2 canonica dalla colonna ``characters.card_json`` by name.

    Ritorna il dict ``{spec, spec_version, data{...}}`` oppure ``None`` se il
    personaggio non esiste. Se la riga esiste ma ``card_json`` è vuoto/non-JSON,
    ritorna uno scheletro Card V2 vuoto col nome popolato (non-distruttivo).
    """
    cur = conn.cursor()
    cur.execute(
        "SELECT card_json FROM characters WHERE name = ? LIMIT 1",
        (name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    raw = row[0]
    if not raw:
        return empty_card_v2(name)
    try:
        card = json.loads(raw)
    except (ValueError, TypeError):
        return empty_card_v2(name)
    if not isinstance(card, dict):
        return empty_card_v2(name)
    # Normalizza spec/version se assenti, senza distruggere il resto
    card.setdefault("spec", CARD_V2_SPEC)
    card.setdefault("spec_version", CARD_V2_VERSION)
    card.setdefault("data", {})
    return card


def save_card_v2(conn: sqlite3.Connection, name: str, card: Dict[str, Any]) -> bool:
    """Persiste una Card V2 in ``characters.card_json`` per il personaggio ``name``.

    Aggiorna la riga esistente (match by name). Ritorna True se aggiornata,
    False se nessuna riga con quel nome esiste (NON crea la riga: l'inserimento
    passa da :func:`add_character`).
    """
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM characters WHERE name = ? LIMIT 1", (name,))
    if cur.fetchone() is None:
        return False
    payload = json.dumps(card, ensure_ascii=False)
    cur.execute(
        "UPDATE characters SET card_json = ?, "
        "updated_at = strftime('%Y-%m-%dT%H:%M:%SZ','now') WHERE name = ?",
        (payload, name),
    )
    conn.commit()
    return True


def card_get(card: Mapping[str, Any], field: str, default: Any = None) -> Any:
    """Helper get su ``card['data'][field]`` con default sicuro."""
    data = card.get("data") if isinstance(card, Mapping) else None
    if not isinstance(data, Mapping):
        return default
    val = data.get(field, default)
    return val if val is not None else default


def card_set(card: Dict[str, Any], field: str, value: Any) -> None:
    """Helper set su ``card['data'][field]`` (crea ``data`` se assente)."""
    data = card.setdefault("data", {})
    data[field] = value


def card_ext(card: Mapping[str, Any], ns: str = "calliope") -> Dict[str, Any]:
    """Restituisce ``card['data']['extensions'][ns]`` (dict, eventualmente vuoto)."""
    data = card.get("data") if isinstance(card, Mapping) else None
    if not isinstance(data, Mapping):
        return {}
    ext = data.get("extensions")
    if not isinstance(ext, Mapping):
        return {}
    sub = ext.get(ns)
    return dict(sub) if isinstance(sub, Mapping) else {}


def add_character_to_scene(
    conn: sqlite3.Connection,
    scene_id: str,
    character_id: str,
    role: str = "participant",
) -> None:
    """
    Associa un personaggio a una scena.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena.
    character_id:
        ID del personaggio.
    role:
        Ruolo del personaggio nella scena.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scene_characters (scene_id, character_id, role)
        VALUES (?, ?, ?)
        """,
        (scene_id, character_id, role),
    )
    conn.commit()


def list_characters_in_scene(
    conn: sqlite3.Connection, scene_id: str
) -> List[Mapping[str, object]]:
    """
    Recupera tutti i personaggi presenti in una scena.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena.

    Returns
    -------
    List[Mapping[str, object]]
        Lista di dizionari rappresentanti i personaggi.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.*, sc.role
        FROM characters c
        JOIN scene_characters sc ON c.id = sc.character_id
        WHERE sc.scene_id = ?
        """,
        (scene_id,),
    )
    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def update_character_scene_role(
    conn: sqlite3.Connection,
    scene_id: str,
    character_id: str,
    role: str,
) -> bool:
    """
    Aggiorna il ruolo di un personaggio in una scena (WI-43).

    Ritorna True se la coppia (scene_id, character_id) esiste ed è stata
    aggiornata, False altrimenti.
    """
    cur = conn.cursor()
    cur.execute(
        "UPDATE scene_characters SET role = ? WHERE scene_id = ? AND character_id = ?",
        (role, scene_id, character_id),
    )
    conn.commit()
    return cur.rowcount > 0


def remove_character_from_scene(
    conn: sqlite3.Connection, scene_id: str, character_id: str
) -> bool:
    """
    Rimuove un personaggio da una scena.

    Parameters
    ----------
    conn:
        Connessione SQLite attiva.
    scene_id:
        ID della scena.
    character_id:
        ID del personaggio.

    Returns
    -------
    bool
        True se rimosso, False se non era presente.
    """
    cur = conn.cursor()
    cur.execute(
        """
        DELETE FROM scene_characters
        WHERE scene_id = ? AND character_id = ?
        """,
        (scene_id, character_id),
    )
    conn.commit()
    return cur.rowcount > 0
