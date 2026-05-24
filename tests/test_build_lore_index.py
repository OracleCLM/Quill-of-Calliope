"""Sprint F1 — build_lore_index test suite."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


def test_fl1_extract_char_lore(tmp_path):
    char_file = tmp_path / "aurora.draft.yaml"
    char_file.write_text(
        "name: Aurora\nrace: yokai\nclass: queen\ngender: female\n"
        "backstory: A centuries-old yokai queen.\n"
        "traits:\n  - compassionate\n  - regal\n"
        "relationships:\n  Kikyo: close ally\n"
        "behavior_pattern:\n  role: leader\n  decision_style: empathetic\n"
        "  typical_actions:\n    - protects allies\n",
        encoding="utf-8",
    )
    from build_lore_index import _extract_char_lore
    docs = _extract_char_lore(char_file)
    assert len(docs) >= 3
    texts = " ".join(d["text"] for d in docs)
    assert "yokai" in texts
    assert "queen" in texts
    assert "backstory" in texts.lower() or "centuries-old" in texts


def test_fl2_extract_scene_lore(tmp_path):
    scene_file = tmp_path / "scene_test.draft.yaml"
    scene_file.write_text(
        "scene_id: scene_test\ntitle: Battle at the Shrine\n"
        "summary: Aurora defended the shrine against shadow creatures while Kikyo channeled her spiritual powers.\n"
        "participants:\n  - Aurora\n  - Kikyo\n",
        encoding="utf-8",
    )
    from build_lore_index import _extract_scene_lore
    docs = _extract_scene_lore(scene_file)
    assert len(docs) == 1
    assert "shrine" in docs[0]["text"].lower()
    assert docs[0]["meta"]["source"] == "scene"


def test_fl3_empty_backstory_skipped(tmp_path):
    char_file = tmp_path / "empty.yaml"
    char_file.write_text("name: Nobody\nrace: unknown\nbackstory: ''\n", encoding="utf-8")
    from build_lore_index import _extract_char_lore
    docs = _extract_char_lore(char_file)
    assert not any(d["meta"]["type"] == "backstory" for d in docs)


def test_fl4_short_summary_skipped(tmp_path):
    scene_file = tmp_path / "short.yaml"
    scene_file.write_text("scene_id: s1\nsummary: Too short\n", encoding="utf-8")
    from build_lore_index import _extract_scene_lore
    docs = _extract_scene_lore(scene_file)
    assert len(docs) == 0


def test_fl5_build_chromadb(tmp_path):
    chars = tmp_path / "characters"
    chars.mkdir()
    (chars / "test.yaml").write_text(
        "name: TestChar\nrace: elf\nclass: mage\n"
        "backstory: An ancient elven mage who guards the forest.\n",
        encoding="utf-8",
    )
    scenes = tmp_path / "scenes"
    scenes.mkdir()
    (scenes / "s1.yaml").write_text(
        "scene_id: s1\ntitle: Forest Patrol\n"
        "summary: TestChar discovered strange markings on the ancient trees near the border.\n"
        "participants:\n  - TestChar\n",
        encoding="utf-8",
    )

    import build_lore_index as bli
    orig_chars = bli._CHARS_DIR
    orig_scenes = bli._SCENES_DIR
    orig_chroma = bli._CHROMA_PATH
    try:
        bli._CHARS_DIR = chars
        bli._SCENES_DIR = scenes
        bli._CHROMA_PATH = str(tmp_path / "chroma_test")
        count = bli.build(reset=True)
    finally:
        bli._CHARS_DIR = orig_chars
        bli._SCENES_DIR = orig_scenes
        bli._CHROMA_PATH = orig_chroma

    assert count >= 2

    import chromadb
    c = chromadb.PersistentClient(path=str(tmp_path / "chroma_test"))
    col = c.get_collection("calliope_lore")
    assert col.count() >= 2
    results = col.query(query_texts=["elven mage"], n_results=1)
    assert len(results["documents"][0]) > 0
    assert "elf" in results["documents"][0][0].lower() or "mage" in results["documents"][0][0].lower()
