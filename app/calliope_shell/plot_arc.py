"""
Plot arc continuity tracker for Quill of Calliope.

Arc = ordered scene refs + char list + open threads JSON.
Shares data/char_memory.db with char_memory.py.
"""

import json
import logging
import os
import re
import sqlite3
import threading
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

import requests

DB_PATH = Path(__file__).parents[2] / "data" / "char_memory.db"
GATEWAY_URL = os.getenv("GATEWAY_URL", "http://localhost:8766")
_lock = threading.Lock()
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _arc_chroma_client():
    """Singleton ChromaDB PersistentClient for plot-arc semantic search.

    Why: PersistentClient was instantiated per call → connection accumulation
    on long-running sessions (audit P0 #2).
    """
    import chromadb  # noqa: PLC0415
    return chromadb.PersistentClient(str(DB_PATH.parent / "chromadb"))

_VALID_SCENE_TYPES = {
    "action_combat", "mystery_investigation", "dialogue",
    "exploration", "confrontation", "tragedy", "celebration",
}


# ── DB helpers ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    c = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    return c


def init_db() -> None:
    """Create plot_arcs and plot_arc_scenes tables (idempotent)."""
    with _lock, _conn() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS plot_arcs (
                arc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'active',
                chars TEXT DEFAULT '[]',
                open_threads TEXT DEFAULT '[]',
                summary TEXT DEFAULT '',
                summary_updated_at TEXT
            );

            CREATE TABLE IF NOT EXISTS plot_arc_scenes (
                arc_id TEXT,
                scene_order INTEGER,
                scene_id TEXT,
                scene_md_path TEXT,
                scene_summary TEXT DEFAULT '',
                added_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (arc_id, scene_order),
                FOREIGN KEY (arc_id) REFERENCES plot_arcs(arc_id)
            );

            CREATE INDEX IF NOT EXISTS idx_plot_arc_scenes_arc
                ON plot_arc_scenes(arc_id, scene_order);
        """)


def _arc_row_to_dict(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["chars"] = json.loads(d.get("chars") or "[]")
    d["open_threads"] = json.loads(d.get("open_threads") or "[]")
    return d


# ── LLM helper ────────────────────────────────────────────────────────────────

def _groq_ask(prompt: str, timeout: int = 25) -> str:
    """Call groq via gateway, return content string or ''."""
    try:
        resp = requests.post(
            f"{GATEWAY_URL}/llm_ask",
            json={"provider": "groq", "model": "llama-3.3-70b-versatile", "prompt": prompt},
            timeout=timeout,
        )
        if resp.ok:
            data = resp.json()
            return data.get("content") or data.get("result") or ""
    except Exception as exc:
        logger.warning("groq gateway call failed (non-fatal): %s", exc)
    return ""


# ── Core functions ────────────────────────────────────────────────────────────

def create_arc(arc_id: str, title: str, chars: List[str]) -> dict:
    """Create or replace a plot arc. Returns arc dict."""
    init_db()
    with _lock, _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO plot_arcs (arc_id, title, chars) VALUES (?, ?, ?)",
            (arc_id, title, json.dumps(chars)),
        )
    return get_arc(arc_id) or {"arc_id": arc_id, "title": title, "chars": chars}


def get_arc(arc_id: str) -> Optional[dict]:
    """Retrieve arc with its scenes list."""
    init_db()
    with _conn() as c:
        row = c.execute("SELECT * FROM plot_arcs WHERE arc_id = ?", (arc_id,)).fetchone()
        if not row:
            return None
        arc = _arc_row_to_dict(row)
        scenes = [
            dict(r) for r in c.execute(
                "SELECT * FROM plot_arc_scenes WHERE arc_id = ? ORDER BY scene_order", (arc_id,)
            ).fetchall()
        ]
        arc["scenes"] = scenes
    return arc


def list_arcs(status: Optional[str] = None) -> List[dict]:
    """List all arcs, optionally filtered by status."""
    init_db()
    with _conn() as c:
        if status:
            rows = c.execute("SELECT * FROM plot_arcs WHERE status = ?", (status,)).fetchall()
        else:
            rows = c.execute("SELECT * FROM plot_arcs ORDER BY updated_at DESC").fetchall()
        return [_arc_row_to_dict(r) for r in rows]


def append_scene(
    arc_id: str,
    scene_md_path: str,
    scene_summary: Optional[str] = None,
) -> dict:
    """Append scene to arc. Auto-generates summary via groq if not provided."""
    init_db()
    path = Path(scene_md_path)
    if not path.exists():
        logger.warning("append_scene: file not found %s", scene_md_path)
        return {}

    # Extract body text (skip #, **, --- lines)
    text_body = " ".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith(("#", "**", "---", "_"))
    ).strip()

    if scene_summary is None:
        summary_resp = _groq_ask(f"Summarize in 1 sentence this fantasy RPG scene: {text_body[:1200]}")
        scene_summary = summary_resp.strip() or "No summary available."

    with _lock, _conn() as c:
        row = c.execute(
            "SELECT IFNULL(MAX(scene_order), -1) + 1 FROM plot_arc_scenes WHERE arc_id = ?",
            (arc_id,),
        ).fetchone()
        scene_order = row[0] if row else 0
        scene_id = f"{arc_id}_s{scene_order}"
        c.execute(
            "INSERT INTO plot_arc_scenes (arc_id, scene_order, scene_id, scene_md_path, scene_summary) "
            "VALUES (?, ?, ?, ?, ?)",
            (arc_id, scene_order, scene_id, str(path), scene_summary),
        )
        c.execute(
            "UPDATE plot_arcs SET updated_at = CURRENT_TIMESTAMP WHERE arc_id = ?", (arc_id,)
        )

    return {
        "arc_id": arc_id, "scene_order": scene_order,
        "scene_id": scene_id, "scene_md_path": str(path),
        "scene_summary": scene_summary,
    }


def regenerate_summary(arc_id: str) -> str:
    """Aggregate scene summaries → groq → update arc.summary."""
    arc = get_arc(arc_id)
    if not arc or not arc.get("scenes"):
        logger.warning("regenerate_summary: no scenes for arc %s", arc_id)
        return ""
    joined = " | ".join(
        s["scene_summary"] for s in arc["scenes"] if s.get("scene_summary")
    )
    prompt = (
        f"Summarize this RPG arc in 3-5 lines covering character arcs, key events, "
        f"and current status:\n{joined}"
    )
    summary = _groq_ask(prompt).strip() or "Summary unavailable."
    with _lock, _conn() as c:
        c.execute(
            "UPDATE plot_arcs SET summary = ?, summary_updated_at = CURRENT_TIMESTAMP "
            "WHERE arc_id = ?",
            (summary, arc_id),
        )
    return summary


def detect_open_threads(arc_id: str) -> List[dict]:
    """Detect unresolved narrative threads via regex heuristics."""
    arc = get_arc(arc_id)
    if not arc or not arc.get("scenes"):
        return []

    threads: List[dict] = []
    seen_names: set = set()
    name_pat = re.compile(r"\b[A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?\b")
    unresolved_pat = re.compile(
        r"\b(quest|missing|escaped|hiding|unknown|searching|pursuing|betrayed|"
        r"revealed|suspected|disappeared|sought|clue|evidence|secret)\b",
        re.IGNORECASE,
    )
    _SKIP = {"The", "She", "Her", "His", "They", "Their", "Who", "This", "That"}

    for idx, scene in enumerate(arc["scenes"]):
        summary = scene.get("scene_summary", "")
        names = {n for n in name_pat.findall(summary) if n not in _SKIP}
        for name in names - seen_names:
            threads.append({"thread": f"Character: {name}", "last_scene_idx": idx, "type": "character"})
        seen_names.update(names)
        for m in unresolved_pat.finditer(summary):
            threads.append({"thread": f"Unresolved: {m.group(0)}", "last_scene_idx": idx, "type": "event"})

    # Save threads to DB
    with _lock, _conn() as c:
        c.execute(
            "UPDATE plot_arcs SET open_threads = ? WHERE arc_id = ?",
            (json.dumps(threads), arc_id),
        )
    return threads


def propose_next_scene(arc_id: str, hint: Optional[str] = None) -> dict:
    """Propose next scene_type + prompt_seed via groq."""
    arc = get_arc(arc_id)
    if not arc:
        return {}
    scene_context = " | ".join(
        f"S{i}: {s['scene_summary']}" for i, s in enumerate(arc.get("scenes", []))
        if s.get("scene_summary")
    )
    threads_text = "; ".join(t["thread"] for t in arc.get("open_threads", [])) or "none"
    hint_line = f"\nOperator hint: {hint}" if hint else ""
    prompt = (
        f"You are a fantasy RPG narrator. Based on this arc, propose the next scene.\n"
        f"Arc title: {arc['title']}\n"
        f"Characters: {', '.join(arc.get('chars', []))}\n"
        f"Arc summary: {arc.get('summary') or 'Not yet summarized'}\n"
        f"Scene history: {scene_context}\n"
        f"Open threads: {threads_text}{hint_line}\n\n"
        f"Respond with exactly two lines:\n"
        f"scene_type: [one of: action_combat, mystery_investigation, dialogue, exploration, confrontation]\n"
        f"prompt: [50-100 word scene setup]"
    )
    content = _groq_ask(prompt, timeout=30)
    scene_type = "mystery_investigation"
    prompt_seed = ""
    for line in content.splitlines():
        lo = line.lower().strip()
        if lo.startswith("scene_type:"):
            candidate = lo.split(":", 1)[1].strip()
            if candidate in _VALID_SCENE_TYPES:
                scene_type = candidate
        elif lo.startswith("prompt:"):
            prompt_seed = line.split(":", 1)[1].strip()
    if not prompt_seed:
        prompt_seed = content.strip()[:300] or "Continue the arc from where it left off."
    return {"scene_type": scene_type, "prompt_seed": prompt_seed, "hint_used": hint}


# ── ChromaDB search (best-effort, degrades to empty list) ────────────────────

def search_arcs_by_topic(query: str, top_k: int = 3) -> List[dict]:
    """Semantic search across arc summaries via ChromaDB (best-effort)."""
    try:
        client = _arc_chroma_client()
        try:
            col = client.get_or_create_collection("calliope_plot_arcs")
        except Exception:
            col = client.get_or_create_collection("calliope_plot_arcs")

        arcs = list_arcs()
        if arcs:
            docs = [a.get("summary") or a["title"] for a in arcs]
            ids = [a["arc_id"] for a in arcs]
            # Upsert all arc summaries
            col.upsert(documents=docs, ids=ids)

        results = col.query(query_texts=[query], n_results=min(top_k, max(1, len(arcs))))
        out = []
        for doc_id, doc in zip(
            results.get("ids", [[]])[0], results.get("documents", [[]])[0]
        ):
            out.append({"arc_id": doc_id, "summary_excerpt": doc[:200]})
        return out
    except Exception as exc:
        logger.warning("search_arcs_by_topic: ChromaDB unavailable (%s) — returning empty", exc)
        return []
