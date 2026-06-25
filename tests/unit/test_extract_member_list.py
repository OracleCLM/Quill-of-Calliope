"""Unit tests per scripts/extract_member_list.py — fetch_members, _fetch_page, main."""
from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock, patch

import pytest

import scripts.extract_member_list as eml


# ── _fetch_page ───────────────────────────────────────────────────────────────

def _mock_client(status=200, json_data=None, headers=None):
    """Build a MagicMock httpx.Client context manager returning a fake response."""
    mock_resp = MagicMock()
    mock_resp.status_code = status
    mock_resp.json.return_value = json_data or []
    mock_resp.headers = headers or {}
    mock_client_inst = MagicMock()
    mock_client_inst.get.return_value = mock_resp
    mock_client_cm = MagicMock()
    mock_client_cm.__enter__ = MagicMock(return_value=mock_client_inst)
    mock_client_cm.__exit__ = MagicMock(return_value=False)
    return mock_client_cm


def test_fetch_page_200_returns_members():
    members = [{"user": {"id": "1", "username": "Alice"}}]
    cm = _mock_client(200, members)
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm):
        result = eml._fetch_page("http://ex", {}, {}, max_retries=1, initial_backoff=1, max_backoff=2)
    assert result == members


def test_fetch_page_empty_200_returns_empty():
    cm = _mock_client(200, [])
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm):
        result = eml._fetch_page("http://ex", {}, {}, 1, 1, 2)
    assert result == []


def test_fetch_page_429_then_200(capsys):
    members = [{"user": {"id": "99"}}]
    calls = [
        MagicMock(status_code=429, headers={"Retry-After": "1"}, json=MagicMock(return_value=None)),
        MagicMock(status_code=200, headers={}, json=MagicMock(return_value=members)),
    ]
    mock_client_inst = MagicMock()
    mock_client_inst.get.side_effect = calls
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_client_inst)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm), \
         patch("scripts.extract_member_list.time.sleep"):
        result = eml._fetch_page("http://ex", {}, {}, max_retries=2, initial_backoff=1, max_backoff=4)
    assert result == members
    assert "Rate limited" in capsys.readouterr().out


def test_fetch_page_non_200_non_429_retries_then_fails(capsys):
    mock_client_inst = MagicMock()
    mock_client_inst.get.return_value = MagicMock(status_code=403, headers={})
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_client_inst)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm), \
         patch("scripts.extract_member_list.time.sleep"):
        result = eml._fetch_page("http://ex", {}, {}, max_retries=1, initial_backoff=1, max_backoff=2)
    assert result is None
    out = capsys.readouterr().out
    assert "HTTP 403" in out
    assert "Aborting page" in out


def test_fetch_page_exception_retries_then_fails(capsys):
    mock_client_inst = MagicMock()
    mock_client_inst.get.side_effect = ConnectionError("timeout")
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_client_inst)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm), \
         patch("scripts.extract_member_list.time.sleep"):
        result = eml._fetch_page("http://ex", {}, {}, max_retries=1, initial_backoff=1, max_backoff=2)
    assert result is None
    out = capsys.readouterr().out
    assert "Request error" in out


def test_fetch_page_429_no_retry_after_uses_backoff(capsys):
    """429 without Retry-After header falls back to backoff."""
    calls = [
        MagicMock(status_code=429, headers={}, json=MagicMock(return_value=None)),
        MagicMock(status_code=200, headers={}, json=MagicMock(return_value=[])),
    ]
    mock_client_inst = MagicMock()
    mock_client_inst.get.side_effect = calls
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=mock_client_inst)
    cm.__exit__ = MagicMock(return_value=False)
    with patch("scripts.extract_member_list.httpx.Client", return_value=cm), \
         patch("scripts.extract_member_list.time.sleep") as mock_sleep:
        result = eml._fetch_page("http://ex", {}, {}, max_retries=2, initial_backoff=5, max_backoff=60)
    # sleep called once with backoff=5 (not retry_after)
    mock_sleep.assert_called_once_with(5)
    assert result == []


# ── fetch_members ─────────────────────────────────────────────────────────────

def test_fetch_members_single_page_writes_jsonl(tmp_path):
    members = [
        {"user": {"id": "1", "username": "Alice", "global_name": "Alice G", "avatar": None, "bot": False},
         "nick": "Alic", "joined_at": "2024-01-01", "roles": ["role1"]},
    ]
    output = tmp_path / "members.jsonl"
    with patch("scripts.extract_member_list._fetch_page", return_value=members):
        eml.fetch_members("guild1", "token", str(output))
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    data = json.loads(lines[0])
    assert data["username"] == "Alice"
    assert data["user_id"] == "1"
    assert data["roles"] == ["role1"]


def test_fetch_members_two_pages_then_empty(tmp_path, capsys):
    page1 = [
        {"user": {"id": str(i), "username": f"User{i}", "global_name": None, "avatar": None, "bot": False},
         "nick": None, "joined_at": "2024-01-01", "roles": []}
        for i in range(1000)
    ]
    page2 = [
        {"user": {"id": "9999", "username": "Last", "global_name": None, "avatar": None, "bot": False},
         "nick": None, "joined_at": "2024-01-02", "roles": []}
    ]
    output = tmp_path / "members.jsonl"
    with patch("scripts.extract_member_list._fetch_page", side_effect=[page1, page2]):
        eml.fetch_members("g", "t", str(output))
    out = capsys.readouterr().out
    assert "1001" in out or "1000" in out  # progress prints
    lines = output.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1001


def test_fetch_members_none_page_aborts(tmp_path, capsys):
    """_fetch_page returns None → stop gracefully."""
    output = tmp_path / "members.jsonl"
    with patch("scripts.extract_member_list._fetch_page", return_value=None):
        eml.fetch_members("g", "t", str(output))
    assert "Completed" in capsys.readouterr().out
    assert output.exists()


def test_fetch_members_creates_parent_dir(tmp_path):
    nested = tmp_path / "a" / "b" / "members.jsonl"
    with patch("scripts.extract_member_list._fetch_page", return_value=[]):
        eml.fetch_members("g", "t", str(nested))
    assert nested.parent.exists()


def test_fetch_members_cursor_passed_on_next_page(tmp_path):
    """Second call to _fetch_page should include 'after' cursor from last member of page1."""
    page1 = [
        {"user": {"id": "42", "username": "U", "global_name": None, "avatar": None, "bot": False},
         "nick": None, "joined_at": "2024-01-01", "roles": []}
    ] * 1000
    output = tmp_path / "m.jsonl"
    mock_fetch = MagicMock(side_effect=[page1, []])
    with patch("scripts.extract_member_list._fetch_page", mock_fetch):
        eml.fetch_members("g", "t", str(output))
    second_call_params = mock_fetch.call_args_list[1][0][2]  # positional arg: params
    assert second_call_params.get("after") == "42"


# ── main() ────────────────────────────────────────────────────────────────────

def test_main_missing_guild_exits(monkeypatch):
    monkeypatch.setenv("KOY_GUILD_ID", "")
    monkeypatch.setenv("DISCORD_USER_TOKEN", "tok")
    monkeypatch.setattr(sys, "argv", ["prog", "--guild", ""])
    with pytest.raises(SystemExit) as exc:
        eml.main()
    assert exc.value.code != 0


def test_main_missing_token_exits(monkeypatch):
    monkeypatch.delenv("DISCORD_USER_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["prog", "--guild", "gid123", "--token", ""])
    with pytest.raises(SystemExit) as exc:
        eml.main()
    assert exc.value.code != 0


def test_main_calls_fetch_members(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", [
        "prog", "--guild", "gid123", "--token", "tok456",
        "--output", str(tmp_path / "out.jsonl"),
    ])
    with patch("scripts.extract_member_list.fetch_members") as mock_fetch:
        eml.main()
    mock_fetch.assert_called_once_with("gid123", "tok456", str(tmp_path / "out.jsonl"))
