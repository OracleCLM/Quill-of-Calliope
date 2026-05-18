import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "scripts"))
from classify_messages import rule_based_fallback, read_jsonl, write_jsonl

def test_ooc_paren():    assert rule_based_fallback({"content": "(OOC comment)"}) == "OOC"
def test_ic_default():   assert rule_based_fallback({"content": "Aurora steps forward"}) == "IC"
def test_empty_content():assert rule_based_fallback({"content": ""}) == "IC"
def test_no_content_key():assert rule_based_fallback({}) == "IC"
def test_bracket_ooc():  assert rule_based_fallback({"content": "[OOC] clarification"}) == "IC"  # [ not OOC prefix

def test_read_jsonl_round_trip(tmp_path):
    data = [{"content": "Hello"}, {"content": "(OOC)"}]
    f = tmp_path / "test.jsonl"
    f.write_text("\n".join(json.dumps(d) for d in data))
    assert read_jsonl(str(f)) == data

def test_write_then_read(tmp_path):
    data = [{"role": "user", "content": "Test"}]
    f = tmp_path / "out.jsonl"
    write_jsonl(data, str(f))
    assert read_jsonl(str(f)) == data

def test_read_empty_file(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("")
    assert read_jsonl(str(f)) == []


# Task C — meta/art coverage gap (audit fix)
def test_meta_keyword():
    assert rule_based_fallback({"content": "server announcement: downtime"}) == "meta"

def test_meta_admin():
    assert rule_based_fallback({"content": "mod note: please read rules"}) == "meta"

def test_art_keyword():
    assert rule_based_fallback({"content": "new art commission dropped"}) == "art"

def test_art_image():
    assert rule_based_fallback({"content": "check this image out"}) == "art"

def test_ic_no_keyword():
    assert rule_based_fallback({"content": "The warrior stands ready"}) == "IC"
