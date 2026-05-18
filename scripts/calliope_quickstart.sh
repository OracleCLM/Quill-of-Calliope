#!/usr/bin/env bash
set -euo pipefail

REPO=/home/nic/Scrivania/Quill_of_Calliope
LOG_DIR=/tmp/quill_of_calliope
mkdir -p "$LOG_DIR"
cd "$REPO"

echo "=== Quill of Calliope QuickStart ==="

# 1. LLM gateway :8766
if curl -sf http://localhost:8766/health >/dev/null 2>&1; then
  echo "[ok] LLM gateway gia' attivo :8766"
else
  echo "[>>] Avvio LLM gateway..."
  nohup python3 scripts/llm_gateway_http.py >> "$LOG_DIR/gateway.log" 2>&1 &
  sleep 2
fi

# 2. SillyTavern :8001
if curl -sf http://localhost:8001/ >/dev/null 2>&1; then
  echo "[ok] SillyTavern gia' attivo :8001"
else
  echo "[>>] Avvio SillyTavern..."
  (cd external/sillytavern && nohup bash start.sh >> "$LOG_DIR/sillytavern.log" 2>&1 &)
  sleep 5
fi

# 3. Mascot WS :9876 (graceful skip se script non esiste — Sprint 3)
if [ -f scripts/mascot_ws_server.py ]; then
  if ss -ltn 2>/dev/null | grep -q :9876; then
    echo "[ok] Mascot WS gia' attivo :9876"
  else
    echo "[>>] Avvio Mascot WS..."
    nohup python3 scripts/mascot_ws_server.py --port 9876 >> "$LOG_DIR/mascot_ws.log" 2>&1 &
    sleep 1
  fi
else
  echo "[--] mascot_ws_server.py non trovato — skip (Sprint 3 pending)"
fi

# 4. Flask shell :5000
if curl -sf http://localhost:5000/health >/dev/null 2>&1; then
  echo "[ok] Flask shell gia' attivo :5000"
else
  echo "[>>] Avvio Flask shell..."
  nohup python3 -m app.calliope_shell.server >> "$LOG_DIR/flask_shell.log" 2>&1 &
  sleep 2
fi

# 5. Browser
if [ -n "${DISPLAY:-}" ]; then
  xdg-open http://localhost:5000/ &
else
  echo "no DISPLAY — open http://localhost:5000 manually"
fi

echo ""
echo "Quill of Calliope avviato:"
echo "  Flask shell: http://localhost:5000/"
echo "  SillyTavern: http://localhost:8001/"
echo "  Gateway:     http://localhost:8766/health"
echo "  Logs:        $LOG_DIR/"
