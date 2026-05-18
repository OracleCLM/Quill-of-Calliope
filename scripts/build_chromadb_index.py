#!/usr/bin/env python3
"""
Build ChromaDB index for Quill of Calliope project.

Collections:
  calliope_messages   — RP message corpus
  calliope_characters — character sheets from YAML
  calliope_scenes     — scene records from JSONL (optional)
"""

import argparse
import glob
import json
import logging
import os
import subprocess
from typing import Optional

import chromadb
import requests
import yaml
from tqdm import tqdm

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def embed_text(text: str, ollama_host: str) -> list[float]:
    """Call Ollama REST API and return embedding vector."""
    resp = requests.post(
        f"{ollama_host}/api/embeddings",
        json={"model": "nomic-embed-text:v1.5", "prompt": text},
        timeout=60,
    )
    resp.raise_for_status()
    return resp.json()["embedding"]


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Return [text] when short; else split into overlapping char-chunks."""
    if len(text) <= 2000:
        return [text]
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start += chunk_size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Delta-indexing helper
# ---------------------------------------------------------------------------


def is_already_indexed(collection: chromadb.Collection, doc_id: str) -> bool:
    """Return True if doc_id is already present in collection."""
    result = collection.get(ids=[doc_id], include=[])
    return len(result["ids"]) > 0


def filter_existing_ids(
    collection: chromadb.Collection, ids: list[str]
) -> set[str]:
    """Return set of IDs from *ids* that are already in *collection* (batch check)."""
    if not ids:
        return set()
    result = collection.get(ids=ids, include=[])
    return set(result["ids"])


# ---------------------------------------------------------------------------
# Batch upsert helper
# ---------------------------------------------------------------------------


def _flush(
    collection: chromadb.Collection,
    ids: list[str],
    embeddings: list[list[float]],
    documents: list[str],
    metadatas: list[dict],
) -> None:
    if ids:
        collection.upsert(
            ids=ids,
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
        )
    ids.clear()
    embeddings.clear()
    documents.clear()
    metadatas.clear()


# ---------------------------------------------------------------------------
# Indexing functions
# ---------------------------------------------------------------------------


def index_messages(
    col: chromadb.Collection,
    jsonl_path: str,
    ollama_host: str,
    batch_size: int,
    incremental: bool = False,
    since_id: Optional[str] = None,
) -> None:
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    skipped_since_id = 0
    skipped_incremental = 0

    with open(jsonl_path, encoding="utf-8") as f:
        lines = f.readlines()

    # Accumulate chunks before batch-checking incremental filter
    pending: list[tuple[str, str, dict]] = []  # (doc_id, chunk_text, meta)

    for line in tqdm(lines, desc="messages"):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        message = record.get("message") or ""
        if not message:
            continue

        # --since-id filter: applied at message level (before chunking)
        msg_id = str(record.get("message_id", ""))
        if since_id is not None and msg_id and msg_id <= since_id:
            skipped_since_id += 1
            continue

        row_idx = record.get("row_idx", record.get("id", ""))
        base_id = f"calliope_messages:{row_idx}"
        meta = {
            "channel_id": str(record.get("channel_id", "")),
            "author_id": str(record.get("author_id", record.get("player", ""))),
            "timestamp": str(record.get("timestamp", "")),
            "tag": str(record.get("tag", record.get("type", ""))),
            "tupperbox_proxy": str(record.get("tupperbox_proxy", False)),
            "parent_channel_id": str(record.get("parent_channel_id", "")),
            "player_status": str(record.get("player_status") or ""),
        }

        chunks = chunk_text(message)
        for chunk_idx, chunk in enumerate(chunks):
            doc_id = base_id if len(chunks) == 1 else f"{base_id}:chunk{chunk_idx}"
            pending.append((doc_id, chunk, meta))

        # When pending is large enough, flush a batch
        if len(pending) >= batch_size:
            pending_ids = [p[0] for p in pending]
            if incremental:
                existing = filter_existing_ids(col, pending_ids)
            else:
                existing = set()

            for doc_id, chunk, meta in pending:
                if doc_id in existing:
                    skipped_incremental += 1
                    continue
                try:
                    emb = embed_text(chunk, ollama_host)
                except Exception as exc:  # noqa: BLE001
                    print(f"  [WARN] embed failed for {doc_id}: {exc}")
                    continue
                ids.append(doc_id)
                embeddings.append(emb)
                documents.append(chunk)
                metadatas.append(meta)

                if len(ids) >= batch_size:
                    _flush(col, ids, embeddings, documents, metadatas)

            pending.clear()

    # Flush remaining pending
    if pending:
        pending_ids = [p[0] for p in pending]
        if incremental:
            existing = filter_existing_ids(col, pending_ids)
        else:
            existing = set()

        for doc_id, chunk, meta in pending:
            if doc_id in existing:
                skipped_incremental += 1
                continue
            try:
                emb = embed_text(chunk, ollama_host)
            except Exception as exc:  # noqa: BLE001
                print(f"  [WARN] embed failed for {doc_id}: {exc}")
                continue
            ids.append(doc_id)
            embeddings.append(emb)
            documents.append(chunk)
            metadatas.append(meta)

    _flush(col, ids, embeddings, documents, metadatas)

    if since_id is not None:
        print(f"  [delta] skipped {skipped_since_id} messages (since-id filter)")
    if incremental:
        print(f"  [delta] skipped {skipped_incremental} chunks (already in DB)")


def index_characters(
    col: chromadb.Collection,
    chars_dir: str,
    ollama_host: str,
    batch_size: int,
) -> None:
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []
    seen_ids: set[str] = set()

    yaml_files: list[str] = []
    for root, _, files in os.walk(chars_dir):
        for fname in files:
            if fname.endswith(".yaml"):
                yaml_files.append(os.path.join(root, fname))

    for file_path in tqdm(yaml_files, desc="characters"):
        try:
            with open(file_path, encoding="utf-8") as f:
                record = yaml.safe_load(f)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] yaml parse failed {file_path}: {exc}")
            continue

        if not record:
            continue
        slug = record.get("id") or record.get("slug")
        name = record.get("name", "")
        if not slug or not name:  # skip canon/template files without a real name
            continue
        doc_id = f"calliope_characters:{slug}"
        if doc_id in seen_ids:  # deduplicate: first-file wins
            continue
        seen_ids.add(doc_id)
        backstory = record.get("backstory", "") or ""
        personality = record.get("personality", {}) or {}
        traits: list[str] = []
        if isinstance(personality, dict):
            traits = personality.get("traits", []) or []
        if not traits:
            traits = record.get("traits", []) or []
        speech = record.get("speech_pattern", {}) or {}
        speech_notes = speech.get("notes", "") if isinstance(speech, dict) else ""

        doc_text = (
            f"Name: {name}\n"
            f"{backstory}\n"
            f"Traits: {', '.join(str(t) for t in traits)}\n"
            f"Speech: {speech_notes}"
        ).strip()

        try:
            emb = embed_text(doc_text, ollama_host)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] embed failed for {doc_id}: {exc}")
            continue

        meta = {
            "slug": slug,
            "group": str(record.get("group", record.get("type", ""))),
            "tupperbox_id": str(record.get("tupperbox_id", "")),
            "posts_count": str(record.get("posts_count", "")),
            "avatar_url": str(record.get("avatar_url", "")),
        }

        ids.append(doc_id)
        embeddings.append(emb)
        documents.append(doc_text)
        metadatas.append(meta)

        if len(ids) >= batch_size:
            _flush(col, ids, embeddings, documents, metadatas)

    _flush(col, ids, embeddings, documents, metadatas)


def index_scenes(
    col: chromadb.Collection,
    jsonl_path: str,
    ollama_host: str,
    batch_size: int,
) -> None:
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    with open(jsonl_path, encoding="utf-8") as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="scenes"):
        line = line.strip()
        if not line:
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        scene_id = record.get("scene_id")
        if not scene_id:
            continue

        doc_id = f"calliope_scenes:{scene_id}"
        title = record.get("title", "") or ""
        summary = record.get("summary", "") or ""
        doc_text = f"{title}\n{summary}".strip()

        try:
            emb = embed_text(doc_text, ollama_host)
        except Exception as exc:  # noqa: BLE001
            print(f"  [WARN] embed failed for {doc_id}: {exc}")
            continue

        participants = record.get("participants", []) or []
        meta = {
            "scene_id": str(scene_id),
            "timestamp_range": (
                f"{record.get('timestamp_start', '')}/{record.get('timestamp_end', '')}"
            ),
            "char_list": ",".join(str(p) for p in participants),
            "msg_count": str(record.get("message_count", "")),
        }

        ids.append(doc_id)
        embeddings.append(emb)
        documents.append(doc_text)
        metadatas.append(meta)

        if len(ids) >= batch_size:
            _flush(col, ids, embeddings, documents, metadatas)

    _flush(col, ids, embeddings, documents, metadatas)


def index_scenes_yaml(
    col: chromadb.Collection,
    scenes_dir: str,
    ollama_host: str,
    batch_size: int,
) -> None:
    ids: list[str] = []
    embeddings: list[list[float]] = []
    documents: list[str] = []
    metadatas: list[dict] = []

    yaml_files = sorted(glob.glob(os.path.join(scenes_dir, "*.yaml")))
    skipped = 0
    for path in tqdm(yaml_files, desc="scenes-yaml"):
        try:
            with open(path, encoding="utf-8") as fh:
                record = yaml.safe_load(fh)
        except Exception as exc:  # noqa: BLE001
            log.warning("yaml parse failed %s: %s", path, exc)
            skipped += 1
            continue
        if not record or not isinstance(record, dict):
            skipped += 1
            continue
        scene_id = record.get("scene_id")
        if not scene_id:
            skipped += 1
            continue
        doc_id = f"calliope_scenes:{scene_id}"
        title = record.get("title", "") or ""
        summary = record.get("summary", "") or ""
        doc_text = f"{title}\n{summary}".strip()
        try:
            emb = embed_text(doc_text, ollama_host)
        except Exception as exc:  # noqa: BLE001
            log.warning("embed failed %s: %s", doc_id, exc)
            continue
        participants = record.get("participants", []) or []
        meta = {
            "scene_id": str(scene_id),
            "timestamp_range": f"{record.get('timestamp_start', '')}/{record.get('timestamp_end', '')}",
            "char_list": ",".join(str(p) for p in participants),
            "msg_count": str(record.get("message_count", "")),
        }
        ids.append(doc_id)
        embeddings.append(emb)
        documents.append(doc_text)
        metadatas.append(meta)
        if len(ids) >= batch_size:
            _flush(col, ids, embeddings, documents, metadatas)
    _flush(col, ids, embeddings, documents, metadatas)
    if skipped:
        log.info("index_scenes_yaml: skipped %d files", skipped)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Build ChromaDB index for Quill of Calliope"
    )
    parser.add_argument(
        "--input-messages", dest="input_messages", required=True,
        help="Path to JSONL file with messages",
    )
    parser.add_argument(
        "--input-chars", dest="input_chars", required=True,
        help="Directory of YAML character files",
    )
    parser.add_argument(
        "--input-scenes", dest="input_scenes", default=None,
        help="Optional path to JSONL file with scenes",
    )
    parser.add_argument(
        "--input-scenes-dir", dest="input_scenes_dir", default=None,
        help="Directory of YAML scene files (alternative to --input-scenes JSONL)",
    )
    parser.add_argument(
        "--db-path", dest="db_path", default=".chroma_calliope/",
        help="ChromaDB persistent directory (default: .chroma_calliope/)",
    )
    parser.add_argument(
        "--ollama-host", dest="ollama_host", default="http://localhost:11434",
        help="Ollama host URL",
    )
    parser.add_argument(
        "--batch-size", dest="batch_size", type=int, default=64,
        help="Upsert batch size (default: 64)",
    )
    parser.add_argument(
        "--incremental", action="store_true",
        help="Skip documents already present in ChromaDB",
    )
    parser.add_argument(
        "--since-id", dest="since_id", default=None,
        help="Process only messages with message_id > this snowflake (lexicographic)",
    )
    args = parser.parse_args(argv)

    client = chromadb.PersistentClient(path=args.db_path)
    col_msgs = client.get_or_create_collection("calliope_messages", embedding_function=None)
    col_chars = client.get_or_create_collection("calliope_characters", embedding_function=None)
    col_scenes = client.get_or_create_collection("calliope_scenes", embedding_function=None)

    index_messages(
        col_msgs,
        args.input_messages,
        args.ollama_host,
        args.batch_size,
        incremental=args.incremental,
        since_id=args.since_id,
    )
    index_characters(col_chars, args.input_chars, args.ollama_host, args.batch_size)
    if args.input_scenes:
        index_scenes(col_scenes, args.input_scenes, args.ollama_host, args.batch_size)
    if args.input_scenes_dir:
        index_scenes_yaml(col_scenes, args.input_scenes_dir, args.ollama_host, args.batch_size)

    print(f"calliope_messages: {col_msgs.count()} docs")
    print(f"calliope_characters: {col_chars.count()} docs")
    print(f"calliope_scenes: {col_scenes.count()} docs")

    result = subprocess.run(
        ["du", "-sh", args.db_path], capture_output=True, text=True
    )
    print(f"DB size: {result.stdout.strip()}")


if __name__ == "__main__":
    main()
