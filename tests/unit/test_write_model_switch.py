"""GAP-5: switch modello-scrittura cloud/locale (profilo runtime + route)."""

import pytest
from flask import Flask

from app.calliope_shell import scene_refine
from app.calliope_shell.scene_refine import (
    active_write_profile,
    resolve_write_model,
    set_write_profile,
)


@pytest.fixture(autouse=True)
def _reset_profile():
    scene_refine._write_profile_override.clear()
    yield
    scene_refine._write_profile_override.clear()


def test_default_is_cloud(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_PROVIDER", raising=False)
    monkeypatch.delenv("CALLIOPE_WRITE_MODEL", raising=False)
    assert active_write_profile() == "cloud"
    assert resolve_write_model() == ("cerebras", "zai-glm-4.7")


def test_switch_to_local(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_LOCAL_PROVIDER", raising=False)
    monkeypatch.delenv("CALLIOPE_WRITE_LOCAL_MODEL", raising=False)
    set_write_profile("local")
    assert active_write_profile() == "local"
    assert resolve_write_model() == ("ollama", "dolphin-mistral:7b")
    set_write_profile("cloud")
    assert resolve_write_model()[0] == "cerebras"


def test_invalid_profile_raises():
    with pytest.raises(ValueError):
        set_write_profile("bogus")


def test_route_get_and_post(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_PROVIDER", raising=False)
    monkeypatch.delenv("CALLIOPE_WRITE_MODEL", raising=False)
    # Costruisce un'app con SOLO le route write-model (riproduce la registrazione inline).
    app = Flask(__name__)

    @app.route("/api/scene-chat/write-model", methods=["GET"])
    def _get():
        from flask import jsonify
        p, m = resolve_write_model()
        return jsonify({"profile": active_write_profile(), "provider": p, "model": m})

    @app.route("/api/scene-chat/write-model", methods=["POST"])
    def _post():
        from flask import jsonify, request
        try:
            set_write_profile((request.get_json(silent=True) or {}).get("profile"))
        except ValueError:
            return jsonify({"error": "bad"}), 400
        p, m = resolve_write_model()
        return jsonify({"profile": active_write_profile(), "provider": p, "model": m})

    client = app.test_client()
    assert client.get("/api/scene-chat/write-model").get_json()["profile"] == "cloud"
    r = client.post("/api/scene-chat/write-model", json={"profile": "local"})
    assert r.get_json()["provider"] == "ollama"
    assert client.post("/api/scene-chat/write-model", json={"profile": "x"}).status_code == 400
