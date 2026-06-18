"""Sprint D3 — POST /api/scene/revive test suite."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))


def _make_app():
    from app.calliope_shell.server import create_app
    app, _ = create_app()
    app.config["TESTING"] = True
    return app


def _make_scene_file(tmp_path, scene_id="scene_test", status="dormant"):
    f = tmp_path / f"{scene_id}.draft.yaml"
    f.write_text(
        f"scene_id: {scene_id}\n"
        f"title: Test Scene Revival\n"
        f"status: {status}\n"
        f"summary: Aurora and Kikyo met at the shrine.\n"
        f"participants:\n  - Aurora\n  - Kikyo\n"
        f"last_msg_excerpt: Aurora turned to face the darkness.\n"
        f"operator_notes: Key tension — Aurora suspects betrayal.\n",
        encoding="utf-8",
    )
    return f


# TR1 — scene_id required
def test_tr1_revive_requires_scene_id():
    app = _make_app()
    with app.test_client() as c:
        r = c.post("/api/scene/revive", json={})
    assert r.status_code == 400
    assert "scene_id" in r.get_json()["error"]


# TR2 — scene not found returns 404
def test_tr2_revive_scene_not_found(tmp_path):
    with patch("app.calliope_shell.server._SCENES_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/scene/revive", json={"scene_id": "nonexistent"})
    assert r.status_code == 404


# TR3 — valid revive returns scene_context + participants + suggested_reentry
def test_tr3_revive_returns_full_context(tmp_path):
    _make_scene_file(tmp_path)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Revival: Aurora was at the shrine when..."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.server._SCENES_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/scene/revive", json={"scene_id": "scene_test"})

    assert r.status_code == 200
    data = r.get_json()
    assert "scene_context" in data
    assert data["scene_context"]["title"] == "Test Scene Revival"
    assert "suggested_reentry" in data
    assert len(data["suggested_reentry"]) > 0


# TR4 — revive loads dormant scenes
def test_tr4_revive_loads_dormant(tmp_path):
    _make_scene_file(tmp_path, status="dormant")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Scene revival summary."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.server._SCENES_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/scene/revive", json={"scene_id": "scene_test"})

    assert r.status_code == 200
    assert r.get_json()["scene_context"]["status"] == "dormant"


# TR5 — gateway down is graceful (non-fatal)
def test_tr5_revive_gateway_down_graceful(tmp_path):
    _make_scene_file(tmp_path)
    import requests as _req

    with patch("requests.post", side_effect=_req.exceptions.ConnectionError("down")), \
         patch("app.calliope_shell.server._SCENES_DIR", tmp_path):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/scene/revive", json={"scene_id": "scene_test"})

    assert r.status_code == 200
    data = r.get_json()
    assert "unavailable" in data["suggested_reentry"].lower()


# TR6 — audit_trail called
def test_tr6_revive_audit(tmp_path):
    _make_scene_file(tmp_path)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Revival."}
    mock_resp.raise_for_status = MagicMock()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.server._SCENES_DIR", tmp_path), \
         patch("app.calliope_shell.audit_trail.log_event") as mock_audit:
        app = _make_app()
        with app.test_client() as c:
            c.post("/api/scene/revive", json={"scene_id": "scene_test"})

    mock_audit.assert_called_once()
    assert mock_audit.call_args[0][0] == "scene.revive"


# TR7 — GAP-19: DB-FIRST path (scena nel DB SQLite, non YAML)
def test_tr7_revive_db_first(tmp_path):
    """scene_revive trova scena nel DB anche senza file YAML."""
    from unittest.mock import patch, MagicMock
    from app.db import get_db, init_schema, new_id

    db_file = tmp_path / "test.db"
    conn = get_db(str(db_file))
    init_schema(conn)
    scene_id = new_id()
    conn.execute(
        "INSERT INTO scenes (id, title, location) VALUES (?, ?, ?)",
        (scene_id, "Scena DB Revive", "Tempio antico"),
    )
    char_id = new_id()
    conn.execute(
        "INSERT INTO characters (id, name, kind) VALUES (?, ?, ?)",
        (char_id, "AuroraDB", "npc"),
    )
    conn.execute(
        "INSERT INTO scene_characters (scene_id, character_id) VALUES (?, ?)",
        (scene_id, char_id),
    )
    conn.execute(
        "INSERT INTO messages (id, scene_id, author_name, content_original, "
        "ts, source, position_order) VALUES (?, ?, 'AuroraDB', 'Ultimo messaggio DB.', "
        "'2024-01-01T00:00:00Z', 'manual', 0)",
        (new_id(), scene_id),
    )
    conn.commit()
    conn.close()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"result": "Revival DB."}
    mock_resp.raise_for_status = MagicMock()

    # _SCENES_DIR punta a una dir VUOTA (nessun YAML) → deve trovare la scena nel DB
    empty_dir = tmp_path / "empty_scenes"
    empty_dir.mkdir()

    with patch("requests.post", return_value=mock_resp), \
         patch("app.calliope_shell.server._SCENES_DIR", empty_dir), \
         patch("app.db.CALLIOPE_DB_PATH", str(db_file)):
        app = _make_app()
        with app.test_client() as c:
            r = c.post("/api/scene/revive", json={"scene_id": scene_id})

    assert r.status_code == 200
    data = r.get_json()
    assert data["scene_context"]["title"] == "Scena DB Revive"
    assert "AuroraDB" in [p["name"] if isinstance(p, dict) else p for p in data["participants"]]
