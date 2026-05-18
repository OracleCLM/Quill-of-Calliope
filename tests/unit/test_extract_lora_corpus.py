"""Tests for extract_lora_corpus.py — monkeypatch sys.argv for coverage instrumentation."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
import extract_lora_corpus as elc  # noqa: E402

INPUT_FILE = str(Path(__file__).parents[2] / "datasets/yokai_rpg/messages_clean.jsonl")

def _run(monkeypatch, output_dir, extra=None):
    monkeypatch.setattr(sys, "argv", ["elc", "--input", INPUT_FILE, "--output", str(output_dir)] + (extra or []))
    elc.main()

def test_extract_top2(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--top-chars", "2"])
    assert len(list(tmp_path.glob("*.jsonl"))) >= 2

def test_output_schema(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--top-chars", "1"])
    plain = [f for f in tmp_path.glob("*.jsonl") if "_chatml" not in f.name]
    data = json.loads(plain[0].read_text().splitlines()[0])
    assert {"text","char","scene_id","context_prev_msgs","timestamp"} <= data.keys()

def test_chatml_format(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--top-chars", "1"])
    chatml = list(tmp_path.glob("*_chatml.jsonl"))
    assert chatml
    d = json.loads(chatml[0].read_text().splitlines()[0])
    assert "messages" in d and all("role" in m for m in d["messages"])

def test_top_chars_count(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--top-chars", "3"])
    plain = [f for f in tmp_path.glob("*.jsonl") if "_chatml" not in f.name]
    assert len(plain) == 3

def test_context_window_zero(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--top-chars", "1", "--context-window", "0"])
    plain = [f for f in tmp_path.glob("*.jsonl") if "_chatml" not in f.name]
    if plain:
        data = json.loads(plain[0].read_text().splitlines()[0])
        assert data["context_prev_msgs"] == []

def test_unknown_operator(tmp_path, monkeypatch):
    _run(monkeypatch, tmp_path, ["--operator-id", "NoSuchPlayer99999", "--top-chars", "1"])
    assert tmp_path.exists()  # no crash = pass
