#!/usr/bin/env bash
set -euo pipefail

_log() { echo "[calliope-stop] $*"; }

_log "Stopping all Quill of Calliope daemons..."

pkill -f llm_gateway_http.py || true
_log "LLM gateway stopped"

pkill -f "external/sillytavern" || true
_log "SillyTavern stopped"

pkill -f mascot_ws_server.py || true
_log "Mascot WS stopped"

pkill -f "calliope_shell.server" || true
_log "Flask shell stopped"

_log "All Quill of Calliope daemons stopped."
