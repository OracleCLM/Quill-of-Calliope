"""
Tests for scripts/build_chromadb_index.py

Tests:
  1. Deterministic ID for character (slug → calliope_characters:<slug>)
  2. Long text (>2k chars) produces multiple chunk IDs
  3. Upsert idempotency — same record upserted twice stays count=1
"""

import json
import sys
from pathlib import Path

import pytest

# Allow importing from scripts/
sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))

try:
    import chromadb  # noqa: F401
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False

from build_chromadb_index import (  # noqa: E402
    chunk_text,
    index_characters,
    index_messages,
    index_scenes_yaml,
    is_already_indexed,
)

MOCK_EMBEDDING = [0.1] * 768


def mock_embed(text: str, ollama_host: str) -> list[float]:  # noqa: ARG001
    return MOCK_EMBEDDING


# ---------------------------------------------------------------------------
# Test 1 — deterministic ID for character
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_character_deterministic_id(tmp_path: Path, monkeypatch) -> None:
    """Character with slug='alexis-snyder' → id='calliope_characters:alexis-snyder'."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    # Write a minimal character YAML
    char_yaml = tmp_path / "alexis-snyder.draft.yaml"
    char_yaml.write_text(
        "id: alexis-snyder\nname: Alexis Snyder\nbackstory: A wanderer.\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_characters", embedding_function=None)

    index_characters(col, str(tmp_path), "http://localhost:11434", batch_size=64)

    assert col.count() == 1
    result = col.get(ids=["calliope_characters:alexis-snyder"])
    assert result["ids"] == ["calliope_characters:alexis-snyder"]


# ---------------------------------------------------------------------------
# Test 2 — long text produces chunk IDs
# ---------------------------------------------------------------------------


def test_chunk_text_long_produces_multiple_chunks() -> None:
    """A text >2000 chars must produce multiple chunks with correct indices."""
    long_text = "x" * 3000
    chunks = chunk_text(long_text, chunk_size=512, overlap=64)

    assert len(chunks) > 1, "Expected multiple chunks for text >2000 chars"
    # All chunks are non-empty
    for c in chunks:
        assert len(c) > 0
    # First chunk is exactly chunk_size
    assert len(chunks[0]) == 512


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_long_message_chunk_ids(tmp_path: Path, monkeypatch) -> None:
    """Messages >2k chars are indexed with :chunk0, :chunk1 IDs."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    long_message = "A" * 3000
    record = {
        "row_idx": 42,
        "timestamp": "2021-01-01T00:00:00Z",
        "player": "TestPlayer",
        "type": "IC",
        "message": long_message,
    }
    jsonl_file = tmp_path / "messages.jsonl"
    jsonl_file.write_text(json.dumps(record) + "\n", encoding="utf-8")

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_messages", embedding_function=None)

    index_messages(col, str(jsonl_file), "http://localhost:11434", batch_size=64)

    # Should have multiple docs
    count = col.count()
    assert count > 1

    # Check chunk IDs exist
    result0 = col.get(ids=["calliope_messages:42:chunk0"])
    assert result0["ids"] == ["calliope_messages:42:chunk0"]

    result1 = col.get(ids=["calliope_messages:42:chunk1"])
    assert result1["ids"] == ["calliope_messages:42:chunk1"]


# ---------------------------------------------------------------------------
# Test 3 — idempotent upsert
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_upsert_idempotent(tmp_path: Path, monkeypatch) -> None:
    """Indexing the same character twice keeps count=1."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    char_yaml = tmp_path / "char_a.draft.yaml"
    char_yaml.write_text(
        "id: char-alpha\nname: Alpha\nbackstory: First.\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_characters", embedding_function=None)

    # First run
    index_characters(col, str(tmp_path), "http://localhost:11434", batch_size=64)
    assert col.count() == 1

    # Second run — same data, count must remain 1
    index_characters(col, str(tmp_path), "http://localhost:11434", batch_size=64)
    assert col.count() == 1, "Idempotent upsert: duplicate insert must not increase count"


# ---------------------------------------------------------------------------
# Test 4 — --since-id filters old messages
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_since_id_filters_old_messages(tmp_path: Path, monkeypatch) -> None:
    """Messages with message_id <= since_id are skipped; only later ones are indexed."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    messages = [
        {"message_id": str(i * 100), "row_idx": i, "message": f"msg {i}", "timestamp": ""}
        for i in range(1, 6)  # IDs: "100", "200", "300", "400", "500"
    ]
    jsonl_file = tmp_path / "messages.jsonl"
    jsonl_file.write_text(
        "\n".join(json.dumps(m) for m in messages) + "\n", encoding="utf-8"
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_messages", embedding_function=None)

    index_messages(
        col, str(jsonl_file), "http://localhost:11434", batch_size=64,
        since_id="300",
    )

    # Only row_idx 4 ("400") and 5 ("500") should be indexed
    assert col.count() == 2
    assert col.get(ids=["calliope_messages:4"])["ids"] == ["calliope_messages:4"]
    assert col.get(ids=["calliope_messages:5"])["ids"] == ["calliope_messages:5"]
    # row_idx 1,2,3 must be absent
    for i in (1, 2, 3):
        assert col.get(ids=[f"calliope_messages:{i}"])["ids"] == []


# ---------------------------------------------------------------------------
# Test 6 — index_scenes_yaml valid YAML file
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_index_scenes_yaml_valid(tmp_path: Path, monkeypatch) -> None:
    """A valid scene YAML file is indexed with the correct ID."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    scene_yaml = tmp_path / "scene_003.draft.yaml"
    scene_yaml.write_text(
        "scene_id: scene_003\n"
        "title: The Great Battle\n"
        "summary: Heroes clash at the fortress gate.\n"
        "timestamp_start: '2021-01-01T10:00:00Z'\n"
        "timestamp_end: '2021-01-01T12:00:00Z'\n"
        "message_count: 42\n"
        "participants:\n"
        "  - alexis-snyder\n"
        "  - yokai-lord\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_scenes", embedding_function=None)

    index_scenes_yaml(col, str(tmp_path), "http://localhost:11434", batch_size=64)

    assert col.count() == 1
    result = col.get(ids=["calliope_scenes:scene_003"])
    assert result["ids"] == ["calliope_scenes:scene_003"]


# ---------------------------------------------------------------------------
# Test 7 — index_scenes_yaml skips syntax-error YAML
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_index_scenes_yaml_skips_syntax_error(tmp_path: Path, monkeypatch) -> None:
    """A YAML file with syntax errors is skipped; the valid file is still indexed."""
    monkeypatch.setattr("build_chromadb_index.embed_text", mock_embed)

    valid_yaml = tmp_path / "scene_001.yaml"
    valid_yaml.write_text(
        "scene_id: scene_001\n"
        "title: Opening\n"
        "summary: The story begins.\n"
        "participants: []\n",
        encoding="utf-8",
    )

    broken_yaml = tmp_path / "scene_002.yaml"
    broken_yaml.write_text(
        "key: {invalid\n",
        encoding="utf-8",
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_scenes", embedding_function=None)

    index_scenes_yaml(col, str(tmp_path), "http://localhost:11434", batch_size=64)

    assert col.count() == 1
    result = col.get(ids=["calliope_scenes:scene_001"])
    assert result["ids"] == ["calliope_scenes:scene_001"]


# ---------------------------------------------------------------------------
# Test 5 — --incremental skips already-indexed docs
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not CHROMA_AVAILABLE, reason="chromadb not installed")
def test_incremental_skips_existing(tmp_path: Path, monkeypatch) -> None:
    """With --incremental, a document already in ChromaDB is not re-embedded."""
    embed_call_count = {"n": 0}

    def counting_embed(text: str, ollama_host: str) -> list[float]:  # noqa: ARG001
        embed_call_count["n"] += 1
        return MOCK_EMBEDDING

    monkeypatch.setattr("build_chromadb_index.embed_text", counting_embed)

    # Two messages; pre-populate the collection with msg id=1 (row_idx=1)
    messages = [
        {"message_id": "100", "row_idx": 1, "message": "already indexed", "timestamp": ""},
        {"message_id": "200", "row_idx": 2, "message": "new message", "timestamp": ""},
    ]
    jsonl_file = tmp_path / "messages.jsonl"
    jsonl_file.write_text(
        "\n".join(json.dumps(m) for m in messages) + "\n", encoding="utf-8"
    )

    db_path = str(tmp_path / "chroma")
    client = chromadb.PersistentClient(path=db_path)
    col = client.get_or_create_collection("calliope_messages", embedding_function=None)

    # Pre-populate doc for row_idx=1
    col.upsert(
        ids=["calliope_messages:1"],
        embeddings=[MOCK_EMBEDDING],
        documents=["already indexed"],
        metadatas=[{"tag": "pre"}],
    )
    assert is_already_indexed(col, "calliope_messages:1")

    embed_call_count["n"] = 0  # reset counter before the actual run

    index_messages(
        col, str(jsonl_file), "http://localhost:11434", batch_size=64,
        incremental=True,
    )

    # Only 1 embed call: the new message (row_idx=2); row_idx=1 was skipped
    assert embed_call_count["n"] == 1, (
        f"Expected 1 embed call (new msg only), got {embed_call_count['n']}"
    )
    # Both docs present in collection
    assert col.count() == 2
