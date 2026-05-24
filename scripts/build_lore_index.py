"""Build ChromaDB calliope_lore collection from character sheets + scene summaries.

Extracts lore facts from existing data (no manual lore docs required):
- Character YAML: name, race, class, backstory, relationships, origin
- Scene YAML: summary, participants, title (location/event context)

Usage:
    python scripts/build_lore_index.py [--reset]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import chromadb
import yaml

_ROOT = Path(__file__).parent.parent
_CHARS_DIR = _ROOT / "characters"
_SCENES_DIR = _ROOT / "scenes"
_CHROMA_PATH = str(_ROOT / ".chroma_calliope")
_COLLECTION = "calliope_lore"


def _extract_char_lore(path: Path) -> list[dict]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []

    name = raw.get("name", path.stem)
    docs = []

    backstory = (raw.get("backstory") or "").strip()
    if backstory and len(backstory) > 20:
        docs.append({
            "id": f"char_backstory_{name.lower().replace(' ', '_')}",
            "text": f"{name} — backstory: {backstory}",
            "meta": {"source": "character", "char": name, "type": "backstory"},
        })

    race = raw.get("race", "")
    cls = raw.get("class", "")
    origin = raw.get("origin", "")
    gender = raw.get("gender", "")
    age = raw.get("age", "")
    if race or cls:
        identity = f"{name} is a {gender} {race} {cls}".strip()
        if origin and origin != "unknown":
            identity += f" from {origin}"
        if age and age != "unknown":
            identity += f", age {age}"
        traits = raw.get("traits", [])
        if traits:
            identity += f". Traits: {', '.join(traits[:5])}"
        docs.append({
            "id": f"char_identity_{name.lower().replace(' ', '_')}",
            "text": identity,
            "meta": {"source": "character", "char": name, "type": "identity"},
        })

    rels = raw.get("relationships", {})
    if isinstance(rels, dict) and rels:
        rel_text = f"{name} relationships: " + "; ".join(
            f"{k}: {v}" for k, v in list(rels.items())[:10]
        )
        docs.append({
            "id": f"char_rels_{name.lower().replace(' ', '_')}",
            "text": rel_text,
            "meta": {"source": "character", "char": name, "type": "relationships"},
        })

    behavior = raw.get("behavior_pattern", {})
    if isinstance(behavior, dict) and behavior.get("role"):
        role_text = f"{name} role: {behavior['role']}"
        if behavior.get("decision_style"):
            role_text += f", decision style: {behavior['decision_style']}"
        actions = behavior.get("typical_actions", [])
        if actions:
            role_text += f". Actions: {'; '.join(actions[:4])}"
        docs.append({
            "id": f"char_role_{name.lower().replace(' ', '_')}",
            "text": role_text,
            "meta": {"source": "character", "char": name, "type": "role"},
        })

    return docs


def _extract_scene_lore(path: Path) -> list[dict]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return []
    if not isinstance(raw, dict):
        return []

    scene_id = raw.get("scene_id", path.stem)
    summary = (raw.get("summary") or "").strip()
    title = (raw.get("title") or "").strip()
    participants = raw.get("participants", [])

    if not summary or len(summary) < 20:
        return []

    text = f"Scene '{title}': {summary}"
    if participants:
        text += f" (participants: {', '.join(participants[:6])})"

    return [{
        "id": f"scene_lore_{scene_id}",
        "text": text[:500],
        "meta": {
            "source": "scene",
            "scene_id": scene_id,
            "type": "event",
            "participants": ",".join(participants[:6]),
        },
    }]


def build(reset: bool = False) -> int:
    client = chromadb.PersistentClient(path=_CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(_COLLECTION)
        except Exception:
            pass

    col = client.get_or_create_collection(_COLLECTION)

    all_docs: list[dict] = []

    for p in sorted(_CHARS_DIR.glob("*.yaml")):
        all_docs.extend(_extract_char_lore(p))

    for p in sorted(_SCENES_DIR.glob("*.yaml")):
        all_docs.extend(_extract_scene_lore(p))

    if not all_docs:
        print("No lore documents extracted.")
        return 0

    batch_size = 100
    added = 0
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i:i + batch_size]
        col.upsert(
            ids=[d["id"] for d in batch],
            documents=[d["text"] for d in batch],
            metadatas=[d["meta"] for d in batch],
        )
        added += len(batch)

    print(f"Indexed {added} lore docs into {_COLLECTION} ({col.count()} total in collection)")
    return added


def main():
    parser = argparse.ArgumentParser(description="Build calliope_lore ChromaDB index")
    parser.add_argument("--reset", action="store_true", help="Delete and rebuild collection")
    args = parser.parse_args()
    count = build(reset=args.reset)
    sys.exit(0 if count > 0 else 1)


if __name__ == "__main__":
    main()
