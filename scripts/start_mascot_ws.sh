#!/usr/bin/env bash
# Quill of Calliope — Mascot WebSocket Server daemon launcher
# Usage: start_mascot_ws.sh [--stop | --status]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="/tmp/calliope_mascot_ws.pid"
LOG_FILE="/tmp/calliope_mascot_ws.log"
SERVER_SCRIPT="$SCRIPT_DIR/mascot_ws_server.py"
WS_PORT="${CALLIOPE_WS_PORT:-8767}"
HEALTH_URL="http://localhost:$WS_PORT/health"

_log() { echo "[$(date +%T)] $*"; }

case "${1:-}" in
  --stop)
    if [[ -f "$PID_FILE" ]]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        rm -f "$PID_FILE"
        _log "Mascot WS server stopped (pid=$PID)"
      else
        _log "PID $PID not running — cleaning up"
        rm -f "$PID_FILE"
      fi
    else
      _log "No PID file at $PID_FILE — server not running"
    fi
    exit 0
    ;;

  --status)
    if [[ -f "$PID_FILE" ]]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        _log "RUNNING  pid=$PID log=$LOG_FILE"
        curl -s --max-time 2 "$HEALTH_URL" && echo "" || _log "Health check unreachable (port=$WS_PORT)"
        exit 0
      else
        _log "DEAD — stale PID file (pid=$PID)"
        exit 1
      fi
    else
      _log "STOPPED — no PID file"
      exit 1
    fi
    ;;

  ""|--start)
    # Kill stale PID if present
    if [[ -f "$PID_FILE" ]]; then
      OLD_PID=$(cat "$PID_FILE")
      if kill -0 "$OLD_PID" 2>/dev/null; then
        _log "Already running (pid=$OLD_PID)"
        exit 0
      fi
      rm -f "$PID_FILE"
    fi

    cd "$PROJECT_DIR"
    nohup python3 "$SERVER_SCRIPT" --port "$WS_PORT" >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    _log "Mascot WS server started (pid=$(cat "$PID_FILE") port=$WS_PORT)"
    _log "Log: $LOG_FILE"
    ;;

  *)
    echo "Usage: $(basename "$0") [--start | --stop | --status]" >&2
    exit 2
    ;;
esac
