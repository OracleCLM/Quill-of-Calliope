"""MASCOT-PORT regression: ws_server porta default == 9876 (allineata a server.py/README)."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[2] / "shared" / "live2d_mascot" / "server"))


def test_ws_server_default_port_is_9876():
    from ws_server import main  # noqa: PLC0415 — lazy import per sys.path injection

    parser = argparse.ArgumentParser()
    # Rispecchia la logica di main() per estrarre il default.
    parser.add_argument("--port", type=int, default=None)

    import inspect  # noqa: PLC0415
    src = inspect.getsource(main)
    assert "default=9876" in src, (
        "ws_server.py --port default deve essere 9876 (porta canonica mascot), "
        f"trovato: {src[src.find('--port'):src.find('--port')+80]!r}"
    )


def test_server_py_mascot_urls_use_9876():
    server_path = Path(__file__).parents[2] / "app" / "calliope_shell" / "server.py"
    text = server_path.read_text()
    assert "9876" in text, "server.py deve fare riferimento alla porta 9876 per il mascot"
    assert "8767" not in text or text.count("8767") == 0, (
        "server.py non deve contenere riferimenti all'old port 8767"
    )
