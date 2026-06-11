"""Bridge import messaggi Yokai Discord-tuppers (JSONL) -> DB scene-as-chat (messages).

Selezione intelligente (operator-mandate, vedi .planning/CALLIOPE_MESSAGES_IMPORT_PLAN.md):
 (a) SOLO IC con character (tupper); (b) skip system+OOC; (c) IC fuori-scena -> char_sheets;
 (d) char non-matchato -> character_id NULL + author_name.

NB: il RUN reale su datasets/yokai_rpg/messages_clean.jsonl (32598) è GATED su decisione
operatore (privacy + scope). Questo modulo è testato su fixture; non esegue alcun import qui.
"""
from __future__ import annotations


def import_messages_to_db(messages_jsonl_path: str, scenes_json_path: str, db_path: str | None = None) -> dict:
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
    raise NotImplementedError("messages-import bridge: implementazione aider (contract-red-first)")
