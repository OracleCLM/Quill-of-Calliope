#!/usr/bin/env python3
"""Quill of Calliope mascot WebSocket server — thin wrapper.

Delegates to shared/live2d_mascot/server/ws_server.py (repo-agnostic core).
Calliope-specific overrides:
  - LOG_FILE → /tmp/calliope_mascot_ws.log
  - app title → "calliope-mascot-ws"
  - Daemon mode (nohup via start_mascot_ws.sh)
"""

import argparse
import sys
from pathlib import Path
from subprocess import Popen

# Wire shared package onto path
_SHARED = Path(__file__).parent.parent / "shared"
if str(_SHARED) not in sys.path:
    sys.path.insert(0, str(_SHARED))

# Calliope-specific log path (override before shared import)
import live2d_mascot.server.ws_server as _ws_core  # noqa: E402

_ws_core.LOG_FILE = "/tmp/calliope_mascot_ws.log"
_ws_core.WELCOME_MSG = "Calliope mascot WS v1"
_ws_core.app.title = "calliope-mascot-ws"

# Re-export for external consumers
app = _ws_core.app
manager = _ws_core.manager


def main() -> None:
    parser = argparse.ArgumentParser(description="Calliope mascot WebSocket server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9876)
    parser.add_argument("--daemon", action="store_true")
    args = parser.parse_args()

    if args.daemon:
        import subprocess  # noqa: PLC0415
        proc = Popen(
            [sys.executable, __file__, "--host", args.host, "--port", str(args.port)],
            stdout=open("/tmp/calliope_mascot_ws.log", "w"),
            stderr=subprocess.STDOUT,
        )
        Path("/tmp/calliope_mascot_ws.pid").write_text(str(proc.pid))
        print(f"Daemon started PID={proc.pid}")
        return

    import uvicorn  # noqa: PLC0415
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
