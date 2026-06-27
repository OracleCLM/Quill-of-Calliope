import os
import tempfile

from flask import Flask

from app.calliope_shell.scenes_db_routes import register_scenes_db_routes
from app.db import get_db


def test_db_health():
    db_fd, db_path = tempfile.mkstemp()
    app = Flask(__name__)
    app.config["TESTING"] = True

    register_scenes_db_routes(app, db_path=db_path)

    with app.app_context():
        conn = get_db(db_path)
        # Setup minimo schema per il test (evita dipendenza da migration complesse)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS scenes (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                arc_id TEXT,
                location TEXT,
                last_activity_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.execute(
            "INSERT INTO scenes (id, title) VALUES (?, ?)", ("scene_1", "Test")
        )
        conn.commit()
        conn.close()

    client = app.test_client()
    response = client.get("/api/db/health")

    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "ok"
    assert data["scenes"] == 1

    os.close(db_fd)
    os.unlink(db_path)
