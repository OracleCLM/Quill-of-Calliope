"""Regression tests for Sprint B1 — /api/dashboard/snapshot consolidated.

Aggregates daemon health + KB counts + LLM routing + recent activity in
one response. Perf budget: <500ms warm (Q7 operator-mandate).
"""
from __future__ import annotations

import time

import pytest

from app.calliope_shell.server import create_app


@pytest.fixture
def client():
    app, _ = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_snapshot_endpoint_200(client):
    resp = client.get("/api/dashboard/snapshot")
    assert resp.status_code == 200


def test_snapshot_schema_top_level(client):
    data = client.get("/api/dashboard/snapshot").get_json()
    for key in ("daemons", "counts", "llm_routing", "recent_activity",
                "snapshot_latency_ms", "snapshot_taken_at"):
        assert key in data, f"missing top-level key: {key}"


def test_snapshot_daemons_schema(client):
    data = client.get("/api/dashboard/snapshot").get_json()
    daemons = data["daemons"]
    for d_name in ("flask", "llm_gateway", "mascot_ws", "chromadb"):
        assert d_name in daemons
        d = daemons[d_name]
        assert "up" in d and isinstance(d["up"], bool)
        assert "code" in d
        assert "latency_ms" in d


def test_snapshot_no_discord_panel(client):
    """Q6 operator-decision: Discord widget SKIPPED until bot active."""
    data = client.get("/api/dashboard/snapshot").get_json()
    assert "discord" not in data["daemons"]


def test_snapshot_counts_split_active_archive(client):
    """Q2 default: chars split into active (DB) and archive (yaml-only)."""
    data = client.get("/api/dashboard/snapshot").get_json()
    chars = data["counts"]["chars"]
    assert "active" in chars
    assert "archive" in chars
    assert "total_yaml" in chars
    assert chars["active"] + chars["archive"] == chars["total_yaml"]


def test_snapshot_llm_routing_schema(client):
    data = client.get("/api/dashboard/snapshot").get_json()
    routing = data["llm_routing"]
    for k in ("active_provider", "active_model", "uncensored_available", "uncensored_provider"):
        assert k in routing


def test_snapshot_perf_warm_under_500ms(client):
    """Q7 operator-mandate: <500ms warm. Cold first call (chroma init) excluded."""
    client.get("/api/dashboard/snapshot")  # warm-up
    t0 = time.monotonic()
    resp = client.get("/api/dashboard/snapshot")
    elapsed_ms = (time.monotonic() - t0) * 1000
    assert resp.status_code == 200
    assert elapsed_ms < 500, f"warm latency {elapsed_ms:.0f}ms exceeds 500ms budget"


def test_snapshot_self_reports_latency(client):
    data = client.get("/api/dashboard/snapshot").get_json()
    assert isinstance(data["snapshot_latency_ms"], int)
    assert 0 <= data["snapshot_latency_ms"] < 5000


def test_snapshot_recent_activity_is_list(client):
    """Recent activity placeholder until Sprint C audit_trail."""
    data = client.get("/api/dashboard/snapshot").get_json()
    assert isinstance(data["recent_activity"], list)


def test_counts_endpoint_still_available(client):
    """Sprint A3 /api/dashboard/counts must coexist (sidebar widget compat)."""
    resp = client.get("/api/dashboard/counts")
    assert resp.status_code == 200
