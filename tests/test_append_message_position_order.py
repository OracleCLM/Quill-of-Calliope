"""Contract WI-APPEND-ORDER: il path append PRIMARIO scene-as-chat
(POST /api/db/scenes/<id>/messages -> db_append_message) deve assegnare position_order
CRESCENTE (coda), non lasciarlo a 0 di default.

Gap (classe incoerenze-messages): db_append_message chiama add_message SENZA position_order ->
tutti i messaggi appesi finiscono a position_order=0. Tutte le retrieval ordinano ORDER BY
position_order -> con valori tutti-0 lordine e indefinito (regge solo per rowid-tiebreak SQLite,
non garantito) e le feature /move (reorder) e /messages/insert (insert-at-position) sono ROTTE.
Provato: 3 append -> [0,0,0]. Fix: position_order = len(esistenti) prima di add_message.

Contract: append 3 messaggi via la route -> position_order = 0,1,2 (distinti, crescenti).
"""
import sys
from pathlib import Path

import pytest
from flask import Flask

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db import get_db, init_schema  # noqa: E402
from app.calliope_shell.messages_db_routes import register_messages_db_routes  # noqa: E402
from app.db.messages import list_messages_for_scene  # noqa: E402


@pytest.fixture
def client_db(tmp_path):
    p = tmp_path / "t.db"
    conn = get_db(p)
    init_schema(conn)
    conn.execute(
        "INSERT INTO scenes(id, title, created_at, updated_at) "
        "VALUES (?, ?, strftime('%Y-%m-%dT%H:%M:%SZ','now'), strftime('%Y-%m-%dT%H:%M:%SZ','now'))",
        ("sc_a", "Taverna"),
    )
    conn.commit()
    conn.close()
    app = Flask(__name__)
    register_messages_db_routes(app, db_path=str(p))
    return app.test_client(), p


def test_append_assigns_increasing_position_order(client_db):
    client, p = client_db
    for txt in ("primo", "secondo", "terzo"):
        r = client.post("/api/db/scenes/sc_a/messages",
                        json={"author_name": "A", "content_original": txt})
        assert r.status_code == 201
    conn = get_db(p)
    msgs = list_messages_for_scene(conn, "sc_a")
    conn.close()
    positions = [m.get("position_order") for m in msgs]
    assert positions == [0, 1, 2], f"position_order non crescente (gap append): {positions}"
    assert [m["content_original"] for m in msgs] == ["primo", "secondo", "terzo"]
