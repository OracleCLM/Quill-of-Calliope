"""Resilienza-503 del gateway-scrittura: retry/backoff, failover, breaker, route pulita."""

import tempfile

import pytest
from flask import Flask

from app.calliope_shell import scene_refine
from app.calliope_shell.messages_db_routes import register_messages_db_routes
from app.calliope_shell.scene_refine import (
    WriteModelError,
    ask_with_failover,
    reset_circuit_breakers,
)
from app.db import get_db, init_schema
from app.db.messages import add_message, get_message_by_id


class FakeResp:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._body = body or {}
        self.headers = headers or {}

    def json(self):
        return self._body


@pytest.fixture(autouse=True)
def _no_sleep_clean_breakers(monkeypatch):
    monkeypatch.setattr(scene_refine.time, "sleep", lambda *_: None)
    reset_circuit_breakers()
    yield
    reset_circuit_breakers()


def test_retry_then_success(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            return FakeResp(503, {"code": "queue_exceeded"})
        return FakeResp(200, {"content": "OK"})

    monkeypatch.setattr(scene_refine.requests, "post", fake_post)
    assert scene_refine._post_once("cerebras", "m", "p", 5, max_attempts=3) == "OK"
    assert calls["n"] == 3  # ha ritentato due volte


def test_retry_after_header_honored(monkeypatch):
    sleeps = []
    monkeypatch.setattr(scene_refine.time, "sleep", lambda s: sleeps.append(s))
    calls = {"n": 0}

    def fake_post(url, json, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            return FakeResp(503, {}, {"Retry-After": "2"})
        return FakeResp(200, {"content": "OK"})

    monkeypatch.setattr(scene_refine.requests, "post", fake_post)
    assert scene_refine._post_once("cerebras", "m", "p", 5) == "OK"
    assert any(s >= 2 for s in sleeps), "Retry-After non onorato"


def test_no_retry_on_400(monkeypatch):
    calls = {"n": 0}

    def fake_post(url, json, timeout):
        calls["n"] += 1
        return FakeResp(400, {"code": "bad"})

    monkeypatch.setattr(scene_refine.requests, "post", fake_post)
    with pytest.raises(WriteModelError) as ei:
        scene_refine._post_once("cerebras", "m", "p", 5)
    assert ei.value.kind == "bad_request"
    assert calls["n"] == 1  # nessun retry su errore definitivo


def test_no_retry_on_401(monkeypatch):
    monkeypatch.setattr(scene_refine.requests, "post",
                        lambda *a, **k: FakeResp(401, {"code": "invalid_api_key"}))
    with pytest.raises(WriteModelError) as ei:
        scene_refine._post_once("cerebras", "m", "p", 5)
    assert ei.value.kind == "auth"


def test_failover_to_next_provider(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "cerebras")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "m1")
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:m2")

    def fake_post(url, json, timeout):
        if json["provider"] == "cerebras":
            return FakeResp(503, {"code": "queue_exceeded"})
        return FakeResp(200, {"content": "FROM_GROQ"})

    monkeypatch.setattr(scene_refine.requests, "post", fake_post)
    assert ask_with_failover("p") == "FROM_GROQ"


def test_all_providers_fail_raises_overloaded(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "cerebras")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "m1")
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:m2")
    monkeypatch.setattr(scene_refine.requests, "post",
                        lambda *a, **k: FakeResp(503, {"code": "queue_exceeded"}))
    with pytest.raises(WriteModelError) as ei:
        ask_with_failover("p")
    assert ei.value.kind == "overloaded"


def test_circuit_breaker_opens_after_threshold(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "cerebras")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "m1")
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "")  # isola cerebras
    monkeypatch.setattr(scene_refine.requests, "post",
                        lambda *a, **k: FakeResp(503, {"code": "queue_exceeded"}))
    for _ in range(3):
        with pytest.raises(WriteModelError):
            ask_with_failover("p")
    assert scene_refine._breaker_open("cerebras"), "breaker non aperto dopo soglia"


def test_route_returns_clean_503_and_no_clobber(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "")
    monkeypatch.setattr(scene_refine.requests, "post",
                        lambda *a, **k: FakeResp(503, {"code": "queue_exceeded"}))

    _fd, db_path = tempfile.mkstemp(suffix=".db")
    conn = get_db(db_path)
    init_schema(conn)
    sid = "s-503"
    conn.execute("INSERT INTO scenes(id,title,created_at,updated_at) "
                 "VALUES(?,?,datetime('now'),datetime('now'))", (sid, "S"))
    conn.commit()
    mid = add_message(conn, scene_id=sid, author_name="Aria",
                      content_original="Testo originale.")
    conn.close()

    app = Flask(__name__)
    register_messages_db_routes(app, db_path=db_path)
    client = app.test_client()
    resp = client.post(f"/api/db/scenes/{sid}/messages/{mid}/refine")
    assert resp.status_code == 503
    data = resp.get_json()
    assert "sovraccarico" in data["message"].lower()
    assert "error" not in str(data.get("message", "")).lower() or data.get("error")

    # content_enhanced NON deve essere stato sovrascritto (resta None).
    conn = get_db(db_path)
    assert get_message_by_id(conn, mid)["content_enhanced"] is None
    conn.close()


def test_empty_response_treated_as_failure_then_failover(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "cerebras")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "m1")
    monkeypatch.setenv("CALLIOPE_WRITE_FALLBACKS", "groq:m2")

    def fake_post(url, json, timeout):
        if json["provider"] == "cerebras":
            return FakeResp(200, {"content": ""})  # ok-ma-vuoto
        return FakeResp(200, {"content": "REALE"})

    monkeypatch.setattr(scene_refine.requests, "post", fake_post)
    assert ask_with_failover("p") == "REALE"
