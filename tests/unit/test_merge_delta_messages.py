"""Unit test per scripts/merge_delta_messages.py (generato zai-glm, verificato)."""
from __future__ import annotations

import json

import pytest

from scripts.merge_delta_messages import load_existing_ids, main, read_delta_files, transform_message


def test_transform_message_standard():
    dce_msg = {
        "ID": 123456789,
        "Timestamp": "2023-01-01T00:00:00.000000+00:00",
        "Author": {"ID": 987654321, "Name": "TestUser", "Nickname": "TestNick"},
        "Content": "Hello world",
        "Attachments": [{"Url": "http://example.com/img.png"}],
    }
    result = transform_message(dce_msg)
    assert result["message_id"] == "123456789"
    assert result["timestamp"] == "2023-01-01T00:00:00.000000+00:00"
    assert result["author_id"] == "987654321"
    assert result["username"] == "TestUser"
    assert result["nick"] == "TestNick"
    assert result["content"] == "Hello world"
    assert result["attachments"] == ["http://example.com/img.png"]
    assert result["channel_id"] == ""
    assert result["tag"] is None


def test_transform_message_missing_nickname():
    dce_msg = {
        "ID": 1, "Timestamp": "2023-01-01",
        "Author": {"ID": 2, "Name": "User"}, "Content": "No nick", "Attachments": [],
    }
    assert transform_message(dce_msg)["nick"] is None


def test_transform_message_no_attachments():
    dce_msg = {
        "ID": 1, "Timestamp": "2023-01-01",
        "Author": {"ID": 2, "Name": "User"}, "Content": "No att", "Attachments": [],
    }
    assert transform_message(dce_msg)["attachments"] == []


def test_transform_message_multiple_attachments():
    dce_msg = {
        "ID": 1, "Timestamp": "2023-01-01",
        "Author": {"ID": 2, "Name": "User"}, "Content": "Multi",
        "Attachments": [{"Url": "url1"}, {"Url": "url2"}],
    }
    assert transform_message(dce_msg)["attachments"] == ["url1", "url2"]


def test_transform_message_id_string_conversion():
    dce_msg = {
        "ID": 999, "Timestamp": "2023-01-01",
        "Author": {"ID": 888, "Name": "User"}, "Content": "Conv", "Attachments": [],
    }
    result = transform_message(dce_msg)
    assert isinstance(result["message_id"], str)
    assert isinstance(result["author_id"], str)


def test_load_existing_ids_file_not_found(tmp_path):
    assert load_existing_ids(tmp_path / "missing.jsonl") == set()


def test_load_existing_ids_empty_file(tmp_path):
    f = tmp_path / "empty.jsonl"
    f.write_text("", encoding="utf-8")
    assert load_existing_ids(f) == set()


def test_load_existing_ids_single_entry(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('{"message_id": "msg1", "data": "val"}', encoding="utf-8")
    assert load_existing_ids(f) == {"msg1"}


def test_load_existing_ids_multiple_entries(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text(
        '{"message_id": "msg1"}\n{"message_id": "msg2"}\n{"message_id": "msg3"}',
        encoding="utf-8",
    )
    assert load_existing_ids(f) == {"msg1", "msg2", "msg3"}


def test_load_existing_ids_skip_empty_lines(tmp_path):
    f = tmp_path / "data.jsonl"
    f.write_text('{"message_id": "a"}\n\n\n{"message_id": "b"}', encoding="utf-8")
    assert load_existing_ids(f) == {"a", "b"}


def test_load_existing_ids_malformed_json_skipped(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text('{"message_id": "ok"}\nnot json\n{"message_id": "ok2"}', encoding="utf-8")
    result = load_existing_ids(f)
    assert result == {"ok", "ok2"}
    assert "Warning" in capsys.readouterr().out


def test_load_existing_ids_missing_key_skipped(tmp_path, capsys):
    f = tmp_path / "data.jsonl"
    f.write_text('{"message_id": "x"}\n{"other": "y"}\n{"message_id": "z"}', encoding="utf-8")
    result = load_existing_ids(f)
    assert result == {"x", "z"}
    assert "Warning" in capsys.readouterr().out


# ── coverage gaps: read_delta_files + main() ─────────────────────────────────

def _make_dce_msg(msg_id="1", content="Hello", author_id="99"):
    return {
        "ID": msg_id,
        "Timestamp": f"2024-01-0{msg_id}T00:00:00+00:00",
        "Author": {"ID": author_id, "Name": "User"},
        "Content": content,
        "Attachments": [],
    }


def test_read_delta_files_empty_dir(tmp_path, capsys):
    result = read_delta_files(str(tmp_path))
    assert result == []
    assert "No JSON" in capsys.readouterr().out


def test_read_delta_files_valid_list(tmp_path):
    msg = _make_dce_msg()
    (tmp_path / "delta1.json").write_text(json.dumps([msg]), encoding="utf-8")
    result = read_delta_files(str(tmp_path))
    assert len(result) == 1


def test_read_delta_files_dict_not_list_warns(tmp_path, capsys):
    (tmp_path / "bad.json").write_text(json.dumps({"key": "val"}), encoding="utf-8")
    result = read_delta_files(str(tmp_path))
    assert result == []
    assert "Warning" in capsys.readouterr().out


def test_read_delta_files_exception_warns(tmp_path, capsys):
    (tmp_path / "corrupt.json").write_text("{not valid json", encoding="utf-8")
    result = read_delta_files(str(tmp_path))
    assert result == []
    assert "Error" in capsys.readouterr().out


def test_main_no_delta_messages_exits_0(tmp_path, monkeypatch, capsys):
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    output = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
    ])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
    assert "No delta" in capsys.readouterr().out


def test_main_classify_flag_prints_message(tmp_path, monkeypatch, capsys):
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    output = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
        "--classify",
    ])
    with pytest.raises(SystemExit):
        main()
    assert "Classification not implemented" in capsys.readouterr().out


def test_main_full_merge_deduplicates(tmp_path, monkeypatch, capsys):
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    msg1 = _make_dce_msg("1", "First")
    msg2 = _make_dce_msg("2", "Second")
    (delta_dir / "msgs.json").write_text(json.dumps([msg1, msg2, msg1]), encoding="utf-8")
    output = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
    ])
    main()
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    out = capsys.readouterr().out
    assert "1 duplicates" in out


def test_main_sorts_by_timestamp(tmp_path, monkeypatch):
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    msg1 = _make_dce_msg("1", content="Early")
    msg2 = _make_dce_msg("2", content="Late")
    msg1["Timestamp"] = "2024-01-02T00:00:00+00:00"
    msg2["Timestamp"] = "2024-01-01T00:00:00+00:00"
    (delta_dir / "msgs.json").write_text(json.dumps([msg1, msg2]), encoding="utf-8")
    output = tmp_path / "out.jsonl"
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
    ])
    main()
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    records = [json.loads(line) for line in lines]
    assert records[0]["content"] == "Late"
    assert records[1]["content"] == "Early"


def test_main_malformed_line_during_sort(tmp_path, monkeypatch, capsys):
    """Line 109: malformed JSON durante la fase sort → Warning."""
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    msg = _make_dce_msg("1")
    (delta_dir / "msgs.json").write_text(json.dumps([msg]), encoding="utf-8")
    output = tmp_path / "out.jsonl"
    output.write_text('{"message_id":"existing"}\nnot_json\n', encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
    ])
    main()
    assert "Warning" in capsys.readouterr().out


def test_main_blank_lines_in_output_skipped(tmp_path, monkeypatch):
    """Line 105: blank line nel file output durante fase sort → continue."""
    delta_dir = tmp_path / "delta"
    delta_dir.mkdir()
    msg = _make_dce_msg("99")
    (delta_dir / "msgs.json").write_text(json.dumps([msg]), encoding="utf-8")
    output = tmp_path / "out.jsonl"
    output.write_text('\n\n{"message_id":"existing"}\n\n', encoding="utf-8")
    monkeypatch.setattr("sys.argv", [
        "merge_delta_messages.py",
        "--delta-dir", str(delta_dir),
        "--main-output", str(output),
    ])
    main()
    lines = [ln for ln in output.read_text().splitlines() if ln.strip()]
    assert len(lines) >= 1
