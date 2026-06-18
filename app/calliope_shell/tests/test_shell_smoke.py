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


def test_shared_mascot_renderer_served(client):
    # The product shell consumes the shared renderer factory + Mao model via the
    # /shared/live2d_mascot/ route (same source of truth as the dev dashboard).
    r = client.get("/shared/live2d_mascot/frontend/core/renderer.js")
    assert r.status_code == 200
    assert b"createMascotRenderer" in r.data

    m = client.get("/shared/live2d_mascot/models/mao/Mao.model3.json")
    assert m.status_code == 200


def test_shared_mascot_route_blocks_traversal(client):
    # send_from_directory must reject path traversal out of the shared dir.
    r = client.get("/shared/live2d_mascot/../../app/calliope_shell/server.py")
    assert r.status_code in (403, 404)


def test_home_includes_shared_renderer_and_mascot(client, monkeypatch):
    # Regression guard for the two gaps fixed in the mascot-home integration:
    #  1) shell.html must load the shared renderer BEFORE mascot.js;
    #  2) nav-home must resolve to the 'main' panel (the showView('home') alias)
    #     so the Home isn't blanked.
    class _Resp:
        status_code = 200

    monkeypatch.setattr(
        "app.calliope_shell.server.requests.head", lambda *a, **k: _Resp()
    )
    html = client.get("/").data.decode("utf-8")
    assert "/shared/live2d_mascot/frontend/core/renderer.js" in html
    assert 'canvas id="mascot"' in html
    # The 'home' nav alias must be handled in showView (else Home renders blank).
    assert "'home'" in html and "'main'" in html
    # WS URL injected to the client must carry the /mascot path (daemon route),
    # otherwise the emotion-sync handshake 403s.
    assert "9876/mascot" in html
