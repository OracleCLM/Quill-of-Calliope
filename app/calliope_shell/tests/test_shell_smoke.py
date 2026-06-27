import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_root_renders_iframe_when_embed_opted_in(client, monkeypatch):
    # Reversibility guard (R-CALLIOPE-BUG-HOME-ST-IFRAME): the legacy ST iframe
    # is OFF by default and only embeds when the operator opts in via
    # CALLIOPE_EMBED_ST=1 AND ST responds <500. Hermetic: force both.
    class _Resp:
        status_code = 200

    monkeypatch.setenv("CALLIOPE_EMBED_ST", "1")
    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head", lambda *a, **k: _Resp()
    )
    response = client.get("/")
    assert response.status_code == 200
    assert b"localhost:8001" in response.data
    assert b'id="st-iframe"' in response.data


def test_root_renders_native_welcome_by_default(client, monkeypatch):
    # Given-When-Then (resulting-state journey) for the home bug fix.
    # GIVEN no CALLIOPE_EMBED_ST opt-in (default) and a SillyTavern that would
    #       answer <500 (half-init, the exact bug trigger);
    # WHEN  the operator opens the home;
    # THEN  the native welcome-panel renders (scene-as-chat VISION), the dead
    #       ST iframe is NOT embedded, and none of the ST init/error strings
    #       ("inizializzazione", "Settings could not be saved") leak into the page.
    class _Resp:
        status_code = 200  # ST alive but irrelevant — gate is OFF

    monkeypatch.delenv("CALLIOPE_EMBED_ST", raising=False)
    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head", lambda *a, **k: _Resp()
    )
    html = client.get("/").data.decode("utf-8")
    # Native welcome content present
    assert "Quill of Calliope" in html
    assert "Apri Scene-Chat" in html
    # Dead ST iframe NOT embedded
    assert 'id="st-iframe"' not in html
    # No ST init/error toast strings leaked into the served HTML
    assert "inizializzazione" not in html.lower()
    assert "Settings could not be saved" not in html


def test_mascot_state_get(client):
    response = client.get("/api/mascot/state")
    assert response.is_json
    data = response.get_json()
    assert "emotion" in data
    assert "ws_url" in data


def test_root_st_unreachable(client, monkeypatch):
    """Lines 220-221: except branch quando ST non è raggiungibile."""
    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head",
        lambda *a, **k: (_ for _ in ()).throw(ConnectionError("unreachable")),
    )
    response = client.get("/")
    assert response.status_code == 200


def test_mascot_emotion_map(client):
    """Lines 190-195: _load_emotion_map via GET /api/mascot/emotion_map."""
    response = client.get("/api/mascot/emotion_map")
    assert response.status_code == 200
    assert response.is_json


def test_mascot_emotion_map_missing_file(client, monkeypatch, tmp_path):
    """Lines 193-195: except branch in _load_emotion_map quando file mancante."""
    import app.calliope_shell.server as srv
    monkeypatch.setattr(srv.Path, "read_text", lambda *a, **k: (_ for _ in ()).throw(FileNotFoundError("no file")))
    response = client.get("/api/mascot/emotion_map")
    assert response.status_code == 200
    assert response.get_json() == {}


def test_shared_mascot_renderer_served(client):
    r = client.get("/shared/live2d_mascot/frontend/core/renderer.js")
    assert r.status_code == 200
    assert b"createMascotRenderer" in r.data

    m = client.get("/shared/live2d_mascot/models/mao/Mao.model3.json")
    assert m.status_code == 200


def test_shared_mascot_route_blocks_traversal(client):
    r = client.get("/shared/live2d_mascot/../../app/calliope_shell/server.py")
    assert r.status_code in (403, 404)


def test_home_includes_shared_renderer_and_mascot(client, monkeypatch):
    class _Resp:
        status_code = 200

    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head", lambda *a, **k: _Resp()
    )
    html = client.get("/").data.decode("utf-8")
    assert "/shared/live2d_mascot/frontend/core/renderer.js" in html
    assert 'canvas id="mascot"' in html
    assert "'home'" in html and "'main'" in html
    assert "9876/mascot" in html
