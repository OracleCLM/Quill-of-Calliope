#!/usr/bin/env python3
"""Live2D mascot WebSocket server — repo-agnostic shared core.

Provides:
  - ConnectionManager: multi-client WebSocket broadcast
  - FastAPI app with /mascot WS + /health + /event/* REST endpoints
  - Pydantic event models (StateEvent, EmotionEvent, TtsEvent)
  - main() CLI entry point

Usage (standalone):
    python shared/live2d_mascot/server/ws_server.py --port 8767

Usage (thin wrapper in consuming repo):
    from live2d_mascot.server.ws_server import app, main

WebSocket protocol (all messages are JSON):
  Broadcast → clients:
    { "type": "SET_STATE",      "state": str }
    { "type": "SET_EXPRESSION", "expression": str }
    { "type": "TTS_EVENT",      "tts_type": str, "data": dict }
    { "type": "CONNECTED",      "msg": str }

  REST → broadcast:
    POST /event/state    { "state": str }
    POST /event/emotion  { "emotion": str }
    POST /event/tts      { "type": str, "data": dict }

Repo-specific customisation hooks:
  - Override LOG_FILE path before import
  - Subclass ConnectionManager for auth/filtering
  - Register additional FastAPI routes on `app` after import
"""

import argparse
import json
import logging
import sys
from typing import List

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configurable — consuming repo can override before import
LOG_FILE = "/tmp/mascot_ws.log"
WELCOME_MSG = "Live2D mascot WS v1"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stderr),
    ],
)
logger = logging.getLogger("mascot_ws")


# ── Event models ──────────────────────────────────────────────────────────────

class StateEvent(BaseModel):
    state: str


class EmotionEvent(BaseModel):
    emotion: str


class TtsEvent(BaseModel):
    type: str
    data: dict = {}


# ── Connection manager ────────────────────────────────────────────────────────

class ConnectionManager:
    """Multi-client WebSocket broadcast manager."""

    def __init__(self) -> None:
        self.active_connections: List[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.active_connections.append(ws)
        logger.info("Client connected — total: %d", len(self.active_connections))

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self.active_connections:
            self.active_connections.remove(ws)
        logger.info("Client disconnected — total: %d", len(self.active_connections))

    async def broadcast(self, message: dict) -> None:
        dead: list[WebSocket] = []
        for ws in list(self.active_connections):
            try:
                await ws.send_text(json.dumps(message))
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()
app = FastAPI(title="live2d-mascot-ws", version="1.0")

# CORS: il frontend Live2D è servito da un altro origin (l'asset-server in-process
# del desktop-pet, 127.0.0.1:<porta-effimera>) e fa fetch verso questo WS-server
# (es. /tts-status). Senza Access-Control-Allow-Origin, QtWebEngine/Chromium blocca
# ogni fetch cross-origin → flood-CORS in console e fetch falliti (causa-codice G1).
# Servizio puramente LOCALE single-operator → allow_origins="*" è accettabile.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ────────────────────────────────────────────────────────────────────

@app.websocket("/mascot")
async def mascot_ws(ws: WebSocket) -> None:
    await manager.connect(ws)
    try:
        await ws.send_text(json.dumps({"type": "CONNECTED", "msg": WELCOME_MSG}))
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(ws)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "connected_clients": len(manager.active_connections)}


@app.post("/event/state")
async def event_state(ev: StateEvent) -> dict:
    await manager.broadcast({"type": "SET_STATE", "state": ev.state})
    logger.info("broadcast SET_STATE %s", ev.state)
    return {"status": "sent"}


@app.post("/event/emotion")
async def event_emotion(ev: EmotionEvent) -> dict:
    await manager.broadcast({"type": "SET_EXPRESSION", "expression": ev.emotion})
    logger.info("broadcast SET_EXPRESSION %s", ev.emotion)
    return {"status": "sent"}


@app.post("/event/tts")
async def event_tts(ev: TtsEvent) -> dict:
    await manager.broadcast({"type": "TTS_EVENT", "tts_type": ev.type, "data": ev.data})
    logger.info("broadcast TTS_EVENT %s", ev.type)
    return {"status": "sent"}


# ── Twitch event proxy (shared — consuming repo wires twitch_bot.py) ──────────

@app.post("/twitch-event")
async def twitch_event(payload: dict) -> dict:
    """Proxy Twitch bot events to WS clients."""
    event = payload.get("event", "")
    if event == "mascot_state":
        await manager.broadcast({"type": "SET_STATE", "state": payload.get("state", "idle")})
    elif event in ("scene_request", "mood_change"):
        await manager.broadcast({"type": "twitch_event", **payload})
    return {"status": "relayed", "event": event}


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Live2D mascot WebSocket server (shared)")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=9876)
    args = parser.parse_args()
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
