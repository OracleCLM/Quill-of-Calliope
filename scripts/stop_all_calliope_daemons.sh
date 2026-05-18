#!/usr/bin/env bash
# Stop all Quill of Calliope daemons gracefully
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GW_PID="/tmp/calliope_llm_gateway.pid"

_log() { echo "[calliope-stop] $*"; }

# ── 1. Stop Mascot WS ─────────────────────────────────────────────────────────
_log "Stopping Mascot WS server..."
bash "$SCRIPT_DIR/start_mascot_ws.sh" --stop || true

# ── 2. Stop LLM Gateway ───────────────────────────────────────────────────────
_log "Stopping LLM gateway..."
if [[ -f "$GW_PID" ]]; then
  PID=$(cat "$GW_PID")
  if kill -0 "$PID" 2>/dev/null; then
    kill "$PID"
    rm -f "$GW_PID"
    _log "LLM gateway stopped (pid=$PID)"
  else
    _log "LLM gateway PID $PID not running — cleaning up"
    rm -f "$GW_PID"
  fi
else
  _log "LLM gateway not running (no PID file)"
fi

_log "All Quill of Calliope daemons stopped."
