"""Bridge import messaggi Yokai Discord-tuppers (JSONL) -> DB scene-as-chat (messages).

Selezione intelligente (operator-mandate, vedi .planning/CALLIOPE_MESSAGES_IMPORT_PLAN.md):
 (a) SOLO IC con character (tupper); (b) skip system+OOC; (c) IC fuori-scena -> char_sheets;
 (d) char non-matchato -> character_id NULL + author_name.

NB: il RUN reale su datasets/yokai_rpg/messages_clean.jsonl (32598) è GATED su decisione
operatore (privacy + scope). Questo modulo è testato su fixture; non esegue alcun import qui.
"""
from __future__ import annotations

import json

from app.db import get_db, new_id
from app.db.messages import add_message


def import_messages_to_db(
    messages_jsonl_path: str, scenes_json_path: str, db_path: str | None = None
) -> dict:
    """
    Importa i messaggi IC-in-scena nel DB, applicando le 4 regole di selezione.

    Contratto (tests/unit/test_messages_import.py):
      - Carica scenes_json (lista di {scene_id, timestamp_start, timestamp_end}).
      - Per ogni record di messages_jsonl:
          * type in ('system','OOC') o character mancante -> skip (skipped_system_ooc).
          * type=='IC' con character: trova la scena il cui [ts_start, ts_end] contiene il ts.
              - scena trovata -> add_message (character_id per nome se nel DB, altrimenti NULL +
                author_name); ordina per row_idx (position_order). -> messages++
              - nessuna scena -> char_sheets++ (NON è un messaggio-scena, regola c).
      - Idempotente (re-run non duplica).
      - Ritorna {"messages": n, "char_sheets": n, "skipped_system_ooc": n, "char_unmatched": n}.
    """
    # 1. Carica scenes
    with open(scenes_json_path, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    # 2. Connessione DB e mappa personaggi
    conn = get_db(db_path)
    charmap = {
        row["name"]: row["id"]
        for row in conn.execute("SELECT id, name FROM characters").fetchall()
    }

    # 2b. Carica ID scene esistenti nel DB per check FK
    db_scene_ids = {
        r[0] for r in conn.execute("SELECT id FROM scenes").fetchall()
    }

    # 3. Inizializza contatori
    messages = 0
    char_sheets = 0
    skipped_system_ooc = 0
    char_unmatched = 0
    skipped_no_scene = 0

    # 4. Itera sui messaggi
    with open(messages_jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            typ = rec.get("type")
            char = rec.get("character")

            # Skip system/OOC o senza character
            if typ in ("system", "OOC") or not char:
                skipped_system_ooc += 1
                continue

            # 5. Logica IC
            if typ == "IC" and char:
                ts = rec["timestamp"]
                target_scene = None

                # Trova scena contenente il timestamp
                for scene in scenes:
                    if scene["timestamp_start"] <= ts <= scene["timestamp_end"]:
                        target_scene = scene
                        break

                # Nessuna scena trovata -> char_sheets
                if not target_scene:
                    cid = charmap.get(char)
                    content = (
                        rec.get("message") or rec.get("original_message") or ""
                    )
                    row_idx = rec["row_idx"]

                    # Idempotenza
                    existing_sheet = conn.execute(
                        "SELECT 1 FROM character_sheets WHERE character_name=? AND position_order=?",
                        (char, row_idx),
                    ).fetchone()

                    if not existing_sheet:
                        conn.execute(
                            "INSERT INTO character_sheets "
                            "(id, character_name, character_id, content, ts, position_order) "
                            "VALUES (?,?,?,?,?,?)",
                            (
                                new_id(),
                                char,
                                cid,
                                content,
                                rec.get("timestamp"),
                                row_idx,
                            ),
                        )
                        conn.commit()
                        char_sheets += 1

                    continue

                # Scena trovata
                # Check FK: se la scena non è nel DB, salta per evitare errore
                if target_scene["scene_id"] not in db_scene_ids:
                    skipped_no_scene += 1
                    continue

                cid = charmap.get(char)
                if cid is None:
                    char_unmatched += 1

                # 6. Idempotenza e inserimento
                row_idx = rec["row_idx"]
                scene_id = target_scene["scene_id"]

                existing = conn.execute(
                    "SELECT 1 FROM messages WHERE scene_id = ? AND position_order = ?",
                    (scene_id, row_idx),
                ).fetchone()

                if not existing:
                    content = (
                        rec.get("message") or rec.get("original_message") or ""
                    )
                    add_message(
                        conn,
                        scene_id=scene_id,
                        character_id=cid,
                        author_name=char,
                        content_original=content,
                        source="manual",
                        position_order=row_idx,
                    )
                    messages += 1

    # 7. Ritorna statistiche
    return {
        "messages": messages,
        "char_sheets": char_sheets,
        "skipped_system_ooc": skipped_system_ooc,
        "char_unmatched": char_unmatched,
        "skipped_no_scene": skipped_no_scene,
    }
