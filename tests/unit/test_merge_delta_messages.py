"""Unit test per scripts/merge_delta_messages.py (generato zai-glm, verificato)."""
from __future__ import annotations

from scripts.merge_delta_messages import load_existing_ids, transform_message


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
