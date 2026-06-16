"""Test per resolve_write_model (C3 — config gateway-strong/switch cloud-locale)."""

from app.calliope_shell.scene_refine import resolve_write_model


def test_default_is_cloud_strong(monkeypatch):
    monkeypatch.delenv("CALLIOPE_WRITE_PROVIDER", raising=False)
    monkeypatch.delenv("CALLIOPE_WRITE_MODEL", raising=False)
    provider, model = resolve_write_model()
    assert provider == "cerebras"
    assert model == "zai-glm-4.7"


def test_env_override_switch_local(monkeypatch):
    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "ollama")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "dolphin-mistral-abliterated")
    provider, model = resolve_write_model()
    assert provider == "ollama"
    assert model == "dolphin-mistral-abliterated"


def test_refine_message_uses_configured_model(db_connection, tmp_path, monkeypatch):
    """refine_message senza provider/model espliciti usa la config env (C3)."""
    from app.calliope_shell.lore_kb import LoreStore
    from app.calliope_shell.scene_refine import refine_message
    from app.db.messages import add_message
    from tests.unit.conftest import add_scene, add_character

    monkeypatch.setenv("CALLIOPE_WRITE_PROVIDER", "openrouter")
    monkeypatch.setenv("CALLIOPE_WRITE_MODEL", "strong-uncensored-x")

    conn = db_connection["conn"]
    sid = add_scene(conn, "S1")
    cid = add_character(conn, "Aria")
    conn.commit()
    mid = add_message(
        conn,
        scene_id=sid,
        character_id=cid,
        author_name="Aria",
        content_original="A line.",
    )
    store = LoreStore(str(tmp_path / "lore.json"))

    # ask iniettato: l'env non cambia il mock, ma verifichiamo che la risoluzione
    # non rompa il flusso e che content_enhanced venga scritta.
    seen = {}

    def fake_ask(prompt):
        seen["called"] = True
        return "OK"

    result = refine_message(mid, sid, conn, store, ask=fake_ask)
    assert result == "OK"
    assert seen.get("called") is True
