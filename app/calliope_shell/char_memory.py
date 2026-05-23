"""SQLite-backed character state + fact memory for Quill of Calliope.

Extended in Sprint R-CALLIOPE-CHAR-MEMORY-VESTA-PORT-EXTEND:
- char_state table: additive migration (entities column)
- char_facts FTS5 virtual table: fact-level granularity per character
- retrieve_multi_signal: BM25+entity fusion (cosine stub)
- Port pattern from Vesta vesta_minerva_substrate/memory_tree/manager.py
"""
import json
import logging
import sqlite3
import threading
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_DB_PATH = Path(__file__).parents[2] / "data" / "char_memory.db"
_lock = threading.Lock()

_VALID_SCOPES = {"L0", "L1", "L2"}

# Cap on facts scanned per char during entity-overlap signal of
# retrieve_multi_signal (audit P1 #10). Recency-bounded scan trades
# exhaustive coverage for predictable latency on long-lived chars.
_ENTITY_OVERLAP_SCAN_LIMIT = 500


def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    # WAL mode (audit P1 #11): readers no longer block writers.
    # synchronous=NORMAL trades durability-on-crash for ~2x write throughput
    # on the use-case profile (RP narrative, no transactional money).
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    return c


# ── Schema setup ──────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create/migrate DB schema. Non-destructive: additive ALTER TABLE only."""
    try:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        with _lock, _conn() as c:
            c.execute("""
                CREATE TABLE IF NOT EXISTS char_state (
                    name TEXT PRIMARY KEY,
                    traits TEXT,
                    last_action TEXT,
                    relationships TEXT,
                    last_scene_id TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            # Additive migration: entities column
            existing = {row[1] for row in c.execute("PRAGMA table_info(char_state)")}
            if "entities" not in existing:
                c.execute("ALTER TABLE char_state ADD COLUMN entities TEXT DEFAULT '[]'")

            # FTS5 virtual table for fact-level retrieval
            c.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS char_facts USING fts5(
                    fact_id UNINDEXED,
                    char_name,
                    fact_text,
                    entities UNINDEXED,
                    scope UNINDEXED,
                    created_at UNINDEXED,
                    tokenize='unicode61'
                )
            """)
            # Auxiliary real table for metadata lookups by rowid
            c.execute("""
                CREATE TABLE IF NOT EXISTS char_facts_meta (
                    fact_id TEXT PRIMARY KEY,
                    char_name TEXT NOT NULL,
                    scope TEXT NOT NULL DEFAULT 'L1',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
    except Exception as exc:
        logger.warning("char_memory init_db failed: %s", exc)


# ── char_state CRUD ───────────────────────────────────────────────────────────

def get_char(name: str) -> Optional[dict]:
    try:
        with _lock, _conn() as c:
            row = c.execute(
                "SELECT * FROM char_state WHERE name = ?", (name,)
            ).fetchone()
        if row is None:
            return None
        d = dict(row)
        d["traits"] = json.loads(d["traits"] or "{}")
        d["relationships"] = json.loads(d["relationships"] or "{}")
        d["entities"] = json.loads(d.get("entities") or "[]")
        return d
    except Exception as exc:
        logger.warning("char_memory get_char failed: %s", exc)
        return None


def upsert_char(
    name: str,
    traits: Optional[dict] = None,
    last_action: Optional[str] = None,
    relationships: Optional[dict] = None,
    last_scene_id: Optional[str] = None,
) -> None:
    try:
        existing = get_char(name) or {}
        is_new = not bool(existing)
        new_traits = traits if traits is not None else existing.get("traits", {})
        new_rels = relationships if relationships is not None else existing.get("relationships", {})
        new_action = last_action if last_action is not None else existing.get("last_action")
        new_scene = last_scene_id if last_scene_id is not None else existing.get("last_scene_id")
        with _lock, _conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO char_state
                   (name, traits, last_action, relationships, last_scene_id, updated_at)
                   VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
                (
                    name,
                    json.dumps(new_traits),
                    new_action,
                    json.dumps(new_rels),
                    new_scene,
                ),
            )
        # Audit hook (Sprint C2). Differentiate create vs update so the
        # activity feed can use it for highlight mode (create is highlight,
        # update is verbose-only).
        from app.calliope_shell import audit_trail  # noqa: PLC0415
        audit_trail.log_event(
            "char.create" if is_new else "char.update",
            subject=name,
            detail=last_action,
        )
    except Exception as exc:
        logger.warning("char_memory upsert_char failed: %s", exc)


def list_chars() -> list:
    try:
        with _lock, _conn() as c:
            rows = c.execute(
                "SELECT name, traits, updated_at FROM char_state ORDER BY updated_at DESC"
            ).fetchall()
        result = []
        for row in rows:
            traits_data = json.loads(row["traits"] or "{}")
            personality = traits_data.get("personality", [])
            summary = ", ".join(personality[:3]) if personality else ""
            result.append({
                "name": row["name"],
                "traits_summary": summary,
                "updated_at": row["updated_at"],
            })
        return result
    except Exception as exc:
        logger.warning("char_memory list_chars failed: %s", exc)
        return []


def delete_char(name: str) -> bool:
    try:
        with _lock, _conn() as c:
            cur = c.execute("DELETE FROM char_state WHERE name = ?", (name,))
        return cur.rowcount > 0
    except Exception as exc:
        logger.warning("char_memory delete_char failed: %s", exc)
        return False


# ── char_facts CRUD ───────────────────────────────────────────────────────────

def append_fact(
    char_name: str,
    fact_text: str,
    scope: str = "L1",
    entities: Optional[list] = None,
) -> Optional[str]:
    """Insert a new fact into char_facts FTS5 table. Returns fact_id."""
    if scope not in _VALID_SCOPES:
        logger.warning("append_fact: invalid scope %r", scope)
        return None
    if scope == "L0":
        logger.warning("append_fact: L0 is protected, use L1 or L2")
        return None
    try:
        from app.calliope_shell.entity_linker import extract_entities_for_fact  # noqa: PLC0415
        fact_id = str(uuid.uuid4())
        if entities is None:
            extracted = extract_entities_for_fact(fact_text, fact_id)
            entities = extracted
        ents_json = json.dumps([{"name": e["name"], "label": e["label"]} for e in entities])
        with _lock, _conn() as c:
            c.execute(
                "INSERT INTO char_facts(fact_id, char_name, fact_text, entities, scope, created_at) "
                "VALUES(?,?,?,?,?,CURRENT_TIMESTAMP)",
                (fact_id, char_name, fact_text, ents_json, scope),
            )
            c.execute(
                "INSERT OR REPLACE INTO char_facts_meta(fact_id, char_name, scope) VALUES(?,?,?)",
                (fact_id, char_name, scope),
            )
        logger.info("append_fact: %s → %s [%s]", char_name, fact_id[:8], scope)
        # Audit hook (Sprint C2). detail = truncated fact text for activity feed.
        from app.calliope_shell import audit_trail  # noqa: PLC0415
        audit_trail.log_event(
            "char.fact_append",
            subject=char_name,
            detail=fact_text[:200],
            metadata={"fact_id": fact_id, "scope": scope, "n_entities": len(entities)},
        )
        return fact_id
    except Exception as exc:
        logger.warning("char_memory append_fact failed: %s", exc)
        return None


def replace_fact(
    char_name: str,
    old_text: str,
    new_text: str,
    scope: str = "L1",
) -> dict:
    """Replace old_text in facts for char_name. Returns {replaced: N, fact_ids: [...]}."""
    if scope == "L0":
        return {"success": False, "error": "L0 is protected"}
    if scope not in _VALID_SCOPES:
        return {"success": False, "error": f"invalid scope {scope!r}"}
    try:
        with _lock, _conn() as c:
            rows = c.execute(
                "SELECT rowid, fact_id, fact_text FROM char_facts "
                "WHERE char_name = ? AND scope = ?",
                (char_name, scope),
            ).fetchall()
            updated = []
            for row in rows:
                if old_text in row["fact_text"]:
                    new_fact = row["fact_text"].replace(old_text, new_text)
                    c.execute(
                        "UPDATE char_facts SET fact_text = ? WHERE rowid = ?",
                        (new_fact, row["rowid"]),
                    )
                    updated.append(row["fact_id"])
        if updated:
            # Audit hook (Sprint C2).
            from app.calliope_shell import audit_trail  # noqa: PLC0415
            audit_trail.log_event(
                "char.fact_replace",
                subject=char_name,
                detail=f"'{old_text[:80]}' → '{new_text[:80]}'",
                metadata={"replaced": len(updated), "scope": scope},
            )
        return {"success": True, "replaced": len(updated), "fact_ids": updated}
    except Exception as exc:
        logger.warning("char_memory replace_fact failed: %s", exc)
        return {"success": False, "error": str(exc)}


def get_facts(char_name: str, scope: Optional[str] = None) -> list[dict]:
    """Return all facts for char_name, optionally filtered by scope."""
    try:
        with _lock, _conn() as c:
            if scope:
                rows = c.execute(
                    "SELECT fact_id, char_name, fact_text, entities, scope, created_at "
                    "FROM char_facts WHERE char_name = ? AND scope = ?",
                    (char_name, scope),
                ).fetchall()
            else:
                rows = c.execute(
                    "SELECT fact_id, char_name, fact_text, entities, scope, created_at "
                    "FROM char_facts WHERE char_name = ?",
                    (char_name,),
                ).fetchall()
        return [dict(r) for r in rows]
    except Exception as exc:
        logger.warning("char_memory get_facts failed: %s", exc)
        return []


# ── Multi-signal retrieval ────────────────────────────────────────────────────

def retrieve_multi_signal(
    char_name: str,
    query: str,
    top_k: int = 5,
    w_bm25: float = 0.6,
    w_entity: float = 0.4,
) -> list[dict]:
    """Fuse BM25 (FTS5) + entity overlap signals; return top_k ranked facts.

    Weights match Vesta effective defaults (cosine stub redistributes 0.40+0.40
    cosine → 0.60 BM25 / 0.40 entity when cosine unavailable).
    Cosine is a stub (weight redistributed to BM25+entity per Vesta pattern).
    Ported from Vesta vesta_minerva_substrate/memory_tree/manager.py::retrieve_multi_signal.
    """
    limit = top_k * 3

    # ── Signal 1: BM25 via FTS5 ──────────────────────────────────────────────
    bm25_scores: dict[str, float] = {}
    fact_meta: dict[str, dict] = {}
    try:
        with _lock, _conn() as c:
            rows = c.execute(
                "SELECT fact_id, fact_text, entities, scope "
                "FROM char_facts "
                "WHERE char_facts MATCH ? AND char_name = ? "
                "ORDER BY rank LIMIT ?",
                (_fts_escape(query), char_name, limit),
            ).fetchall()
        for i, row in enumerate(rows):
            fid = row["fact_id"]
            bm25_scores[fid] = 1.0 / (1 + i)
            fact_meta[fid] = {
                "fact_text": row["fact_text"],
                "entities": json.loads(row["entities"] or "[]"),
                "scope": row["scope"],
            }
    except Exception as exc:
        logger.warning("retrieve_multi_signal BM25 failed: %s", exc)

    # ── Signal 2: entity overlap ─────────────────────────────────────────────
    # Audit P1 #10: previously this scanned ALL facts per char (O(n)) per
    # query. On chars with 10k+ facts the entity-overlap phase dominated
    # latency. Cap at the most recent _ENTITY_OVERLAP_SCAN_LIMIT facts —
    # narrative recency matters more than exhaustive scan for entity link.
    entity_scores: dict[str, float] = {}
    try:
        from app.calliope_shell.entity_linker import EntityLinker  # noqa: PLC0415
        linker = EntityLinker()
        query_entities = linker.extract_entities(query)
        if query_entities:
            q_names = {e["name"].lower() for e in query_entities}
            q_labels = {e["label"] for e in query_entities}
            with _lock, _conn() as c:
                all_facts = c.execute(
                    "SELECT fact_id, fact_text, entities, scope FROM char_facts "
                    "WHERE char_name = ? ORDER BY created_at DESC LIMIT ?",
                    (char_name, _ENTITY_OVERLAP_SCAN_LIMIT),
                ).fetchall()
            for row in all_facts:
                fid = row["fact_id"]
                fents = json.loads(row["entities"] or "[]")
                hits = sum(
                    1 for e in fents
                    if e.get("name", "").lower() in q_names or e.get("label") in q_labels
                )
                if hits:
                    entity_scores[fid] = hits / max(len(query_entities), 1)
                    fact_meta.setdefault(fid, {
                        "fact_text": row["fact_text"],
                        "entities": fents,
                        "scope": row["scope"],
                    })
    except Exception as exc:
        logger.warning("retrieve_multi_signal entity overlap failed: %s", exc)

    # ── Fusion ───────────────────────────────────────────────────────────────
    all_ids = set(bm25_scores) | set(entity_scores)
    if not all_ids:
        return []

    fused: list[dict] = []
    for fid in all_ids:
        b = bm25_scores.get(fid, 0.0)
        e = entity_scores.get(fid, 0.0)
        score = w_bm25 * b + w_entity * e
        meta = fact_meta.get(fid, {"fact_text": "", "entities": [], "scope": "L1"})
        fused.append({
            "fact_id": fid,
            "fact_text": meta["fact_text"],
            "scope": meta["scope"],
            "score": round(score, 6),
            "signals": {"bm25": round(b, 6), "entity": round(e, 6)},
        })

    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:top_k]


_FTS_PREFIX_LEN = 5  # chars for morphological prefix matching (IT stem ~5)


def _fts_escape(query: str) -> str:
    """Build FTS5 MATCH query — OR between tokens + prefix variants.

    Strategy: exact-token OR prefix-truncated* for tokens ≥8 chars.
    Prefix matching catches Italian morphological variants (addestra/addestrare,
    combatte/combattimento). Ported parity with Vesta _sanitize_fts5 approach.
    """
    tokens = [t.replace('"', '').replace("'", "").strip()
              for t in query.strip().split() if len(t.strip()) >= 2]
    if not tokens:
        return '""'
    parts = []
    for t in tokens:
        parts.append(f'"{t}"')
        # Add prefix variant for long tokens (catches morphological forms)
        if len(t) >= 8:
            prefix = t[:_FTS_PREFIX_LEN]
            parts.append(f'"{prefix}"*')
    return " OR ".join(parts)


init_db()
