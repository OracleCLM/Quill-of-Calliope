#!/usr/bin/env bash
# Start all Quill of Calliope daemons: LLM gateway (8766) + Mascot WS (8767)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
GW_PID="/tmp/calliope_llm_gateway.pid"
GW_LOG="/tmp/calliope_llm_gateway.log"

_log() { echo "[calliope-start] $*"; }
_ok()  { echo "[calliope-start] ✓ $*"; }
_err() { echo "[calliope-start] ✗ $*" >&2; }

cd "$PROJECT_DIR"

# ── 1. LLM Gateway HTTP (port 8766) ──────────────────────────────────────────
_log "Starting LLM gateway on :8766..."
if [[ -f "$GW_PID" ]] && kill -0 "$(cat "$GW_PID")" 2>/dev/null; then
  _ok "LLM gateway already running (pid=$(cat "$GW_PID"))"
else
  rm -f "$GW_PID"
  nohup python3 scripts/llm_gateway_http.py >>"$GW_LOG" 2>&1 &
  echo $! > "$GW_PID"
  sleep 1
  if curl -sf --max-time 3 http://localhost:8766/health &>/dev/null; then
    _ok "LLM gateway started (pid=$(cat "$GW_PID"))"
  else
    _log "LLM gateway starting (health not yet ready — check $GW_LOG)"
  fi
fi

# ── 2. Mascot WebSocket Server (port 8767) ────────────────────────────────────
_log "Starting Mascot WS server on :8767..."
bash "$SCRIPT_DIR/start_mascot_ws.sh" --start
sleep 1
bash "$SCRIPT_DIR/start_mascot_ws.sh" --status || true

_ok "All daemons started. Dashboard: python3 -m http.server 8080"
