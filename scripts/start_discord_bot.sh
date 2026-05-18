#!/usr/bin/env bash
# Start/stop/status Calliope Discord bot daemon
set -euo pipefail
PID_FILE="/tmp/calliope_discord_bot.pid"
LOG_FILE="/tmp/calliope_discord_bot.log"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BOT_SCRIPT="$SCRIPT_DIR/discord_bot.py"

_status() {
    [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null
}

case "${1:-start}" in
  start)
    if _status; then echo "Already running (PID $(cat $PID_FILE))"; exit 0; fi
    if [[ -z "${CALLIOPE_DISCORD_BOT_TOKEN:-}" ]]; then
        echo "ERROR: CALLIOPE_DISCORD_BOT_TOKEN not set. Export it before starting."; exit 1
    fi
    nohup python3 "$BOT_SCRIPT" >> "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    echo "Started PID=$! — log: $LOG_FILE"
    ;;
  stop)
    if _status; then kill "$(cat "$PID_FILE")"; rm -f "$PID_FILE"; echo "Stopped."; else echo "Not running."; fi
    ;;
  status)
    if _status; then echo "Running (PID $(cat $PID_FILE))"; else echo "Not running."; fi
    ;;
  *) echo "Usage: $0 {start|stop|status}"; exit 1;;
esac
