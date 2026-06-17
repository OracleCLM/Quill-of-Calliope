"""Test POST /api/characters — crea un draft.yaml visibile nella griglia Personaggi.

Filesystem isolato via CALLIOPE_CHARS_DIR (nessuna scrittura nel repo).
"""

import tempfile

from flask import Flask

from app.calliope_shell.characters_routes import register_character_routes


def test_create_character_creates_draft_and_lists(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="chars-test-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", tmp)

    app = Flask(__name__)
    register_character_routes(app)
    client = app.test_client()

    # name mancante -> 400
    assert client.post("/api/characters", json={}).status_code == 400

    # crea
    resp = client.post("/api/characters", json={"name": "Aria del Nord"})
    assert resp.status_code == 201
    stem = resp.get_json()["stem"]
    assert stem == "aria-del-nord"

    # il draft.yaml esiste nella dir isolata
    import os
    assert os.path.isfile(os.path.join(tmp, f"{stem}.draft.yaml"))

    # ora compare in GET /api/characters (la fonte della griglia)
    listed = client.get("/api/characters").get_json()
    names = [c.get("name") for c in listed]
    assert "Aria del Nord" in names


def test_create_character_no_overwrite(monkeypatch):
    tmp = tempfile.mkdtemp(prefix="chars-test-")
    monkeypatch.setenv("CALLIOPE_CHARS_DIR", tmp)
    app = Flask(__name__)
    register_character_routes(app)
    client = app.test_client()

    s1 = client.post("/api/characters", json={"name": "Duca"}).get_json()["stem"]
    s2 = client.post("/api/characters", json={"name": "Duca"}).get_json()["stem"]
    assert s1 == "duca"
    assert s2 == "duca-1"  # non sovrascrive
