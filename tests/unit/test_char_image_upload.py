"""
Contract test (father-authored acceptance) — WI-6.

Il worker Efesto deve far passare questi test aggiungendo in
`app/calliope_shell/characters_routes.py`:

    POST /api/characters/<stem>/image   (multipart/form-data, campo "image")
    - 404 se stem sconosciuto
    - 400 se campo "image" assente
    - 200 + {"image_path": "media/characters/<stem><ext>"} se ok
    - File salvato fisicamente in <static_folder>/media/characters/

La route DEVE usare current_app.static_folder per costruire il path di
destinazione (cosi' il test puo' isolare la directory con tmp_path).

NON modificare le assertion: sono il contratto di accettazione.
"""
import io

import pytest
from flask import Flask

from app.calliope_shell.characters_routes import register_character_routes

# Stem reale presente in characters/*.draft.yaml — get_card_v3 ritorna non-None
REAL_STEM = "arianna"

# PNG minimo valido (1x1 pixel, 67 byte) — basta per testare il salvataggio
_MINIMAL_PNG = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx"
    b"\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00"
    b"\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture
def client(tmp_path):
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    app = Flask(__name__, static_folder=str(static_dir))
    app.config["TESTING"] = True
    register_character_routes(app)
    return app.test_client(), static_dir


# --- WI-6: upload immagine --------------------------------------------------

def test_upload_image_ok(client):
    c, static_dir = client
    data = {"image": (io.BytesIO(_MINIMAL_PNG), "avatar.png")}
    r = c.post(
        f"/api/characters/{REAL_STEM}/image",
        data=data,
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert "image_path" in body
    # Il file deve esistere fisicamente sul disco
    saved = static_dir / body["image_path"]
    assert saved.exists(), f"File non salvato: {saved}"
    assert saved.stat().st_size > 0


def test_upload_image_path_contains_stem(client):
    c, static_dir = client
    data = {"image": (io.BytesIO(_MINIMAL_PNG), "avatar.png")}
    r = c.post(
        f"/api/characters/{REAL_STEM}/image",
        data=data,
        content_type="multipart/form-data",
    )
    assert r.status_code == 200
    body = r.get_json()
    assert REAL_STEM in body["image_path"]


def test_upload_image_unknown_stem_404(client):
    c, _ = client
    data = {"image": (io.BytesIO(_MINIMAL_PNG), "avatar.png")}
    r = c.post(
        "/api/characters/personaggio-inesistente-xyz/image",
        data=data,
        content_type="multipart/form-data",
    )
    assert r.status_code == 404


def test_upload_image_missing_field_400(client):
    c, _ = client
    r = c.post(
        f"/api/characters/{REAL_STEM}/image",
        data={},
        content_type="multipart/form-data",
    )
    assert r.status_code == 400
