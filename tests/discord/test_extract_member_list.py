"""Tests for scripts/extract_member_list.py — mock httpx, no real Discord calls."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
import extract_member_list  # noqa: E402


def _make_member(uid: str) -> dict:
    return {
        "user": {
            "id": uid,
            "username": f"user_{uid}",
            "global_name": f"global_{uid}",
            "avatar": None,
            "bot": False,
        },
        "nick": f"nick_{uid}",
        "joined_at": "2023-01-01T00:00:00Z",
        "roles": ["role_1"],
    }


def _mock_resp(status: int, body, headers: dict | None = None):
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body
    resp.headers = headers or {}
    resp.text = str(body)
    return resp


class TestFetchMembers:
    @patch("extract_member_list.time.sleep")
    @patch("extract_member_list.httpx.Client")
    def test_pagination_three_pages(self, mock_client_cls, mock_sleep, tmp_path):
        page1 = [_make_member(str(i)) for i in range(1000)]
        page2 = [_make_member(str(i + 1000)) for i in range(1000)]
        page3 = [_make_member(str(i + 2000)) for i in range(50)]

        client_inst = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client_inst
        client_inst.get.side_effect = [
            _mock_resp(200, page1),
            _mock_resp(200, page2),
            _mock_resp(200, page3),
            _mock_resp(200, []),  # termination
        ]

        out = tmp_path / "members.jsonl"
        extract_member_list.fetch_members("guild123", "token_xyz", str(out))

        lines = out.read_text().splitlines()
        assert len(lines) == 2050
        data = [json.loads(line) for line in lines]
        assert data[0]["user_id"] == "0"
        assert data[2049]["user_id"] == "2049"
        mock_sleep.assert_not_called()

    @patch("extract_member_list.time.sleep")
    @patch("extract_member_list.httpx.Client")
    def test_rate_limit_backoff(self, mock_client_cls, mock_sleep, tmp_path):
        member = [_make_member("42")]
        client_inst = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client_inst
        client_inst.get.side_effect = [
            _mock_resp(429, {}, {"Retry-After": "2"}),
            _mock_resp(429, {}, {"Retry-After": "2"}),
            _mock_resp(200, member),
            _mock_resp(200, []),
        ]

        out = tmp_path / "members.jsonl"
        extract_member_list.fetch_members("guild123", "token_xyz", str(out))

        assert mock_sleep.call_count >= 2
        mock_sleep.assert_any_call(2)
        lines = out.read_text().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["user_id"] == "42"

    @patch("extract_member_list.time.sleep")
    @patch("extract_member_list.httpx.Client")
    def test_empty_guild(self, mock_client_cls, mock_sleep, tmp_path):
        client_inst = MagicMock()
        mock_client_cls.return_value.__enter__.return_value = client_inst
        client_inst.get.return_value = _mock_resp(200, [])

        out = tmp_path / "members.jsonl"
        extract_member_list.fetch_members("guild123", "token_xyz", str(out))

        assert out.exists()
        assert out.read_text() == ""
        mock_sleep.assert_not_called()
        assert client_inst.get.call_count == 1
