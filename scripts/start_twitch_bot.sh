#!/usr/bin/env bash
# Quill of Calliope — Twitch Bot daemon launcher
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PID_FILE="/tmp/calliope_twitch_bot.pid"
LOG_FILE="/tmp/calliope_twitch_bot.log"
BOT_SCRIPT="$SCRIPT_DIR/twitch_bot.py"

_log() { echo "[$(date +%T)] $*"; }

_validate_env() {
  local missing=()
  [[ -z "${CALLIOPE_TWITCH_TOKEN:-}" ]] && missing+=("CALLIOPE_TWITCH_TOKEN")
  [[ -z "${CALLIOPE_TWITCH_CHANNEL:-}" ]] && missing+=("CALLIOPE_TWITCH_CHANNEL")
  if [[ ${#missing[@]} -gt 0 ]]; then
    _log "ERROR: Missing env vars: ${missing[*]}"
    _log "Set them in .env or export before running."
    exit 1
  fi
}

case "${1:-}" in
  --stop)
    if [[ -f "$PID_FILE" ]]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"; rm -f "$PID_FILE"
        _log "Twitch bot stopped (pid=$PID)"
      else
        _log "PID $PID not running — cleaning up"; rm -f "$PID_FILE"
      fi
    else
      _log "No PID file — bot not running"
    fi
    exit 0
    ;;

  --status)
    if [[ -f "$PID_FILE" ]]; then
      PID=$(cat "$PID_FILE")
      if kill -0 "$PID" 2>/dev/null; then
        _log "RUNNING pid=$PID channel=${CALLIOPE_TWITCH_CHANNEL:-?} log=$LOG_FILE"
        exit 0
      else
        _log "DEAD — stale PID (pid=$PID)"; exit 1
      fi
    else
      _log "STOPPED — no PID file"; exit 1
    fi
    ;;

  ""|--start)
    if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
      _log "Already running (pid=$(cat "$PID_FILE"))"; exit 0
    fi
    rm -f "$PID_FILE"

    # Source .env if present
    [[ -f "$PROJECT_DIR/.env" ]] && { set -a; source "$PROJECT_DIR/.env"; set +a; }
    _validate_env

    cd "$PROJECT_DIR"
    nohup python3 "$BOT_SCRIPT" >>"$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    _log "Twitch bot started (pid=$(cat "$PID_FILE") channel=${CALLIOPE_TWITCH_CHANNEL})"
    _log "Log: $LOG_FILE"
    ;;

  *)
    echo "Usage: $(basename "$0") [--start | --stop | --status]" >&2; exit 2
    ;;
esac
