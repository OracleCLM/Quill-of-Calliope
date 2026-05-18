# Live2D Mascot Shared Infrastructure — Architecture

**Package**: `shared/live2d_mascot/`
**Version**: v1.0.0 (2026-05-18, extracted from Calliope.AI M3 Phase-2+3)
**Owner**: Calliope.AI repo (primary), consumed by Vesta (secondary)

---

## Rationale: repo-agnostic vs repo-specific split

The Live2D mascot stack was built in Calliope.AI M3 but its core infra is identity-neutral.
Any RP/VTuber project needs the same WebSocket broadcast, state machine, and emotion system.

**Shared** = infrastructure logic with no project-specific data:
- WebSocket protocol + connection manager
- State machine (idle/talking/listening/thinking)
- Emotion expression slots (f00-f06 → 7 emotions)
- Phoneme sync amplitude analysis
- Persistent state (localStorage JSON)
- TTS amplitude-driven lip-sync

**Repo-specific** = personality + pipeline:
- Character identity (Aurora/Minerva/custom .moc3 model)
- Scene narrative pipeline (Calliope-only)
- LLM tier routing (Calliope storytelling-specific)
- Discord/Twitch integration (Calliope M4)
- LoRA corpus (Calliope M5)

---

## Package structure

```
shared/live2d_mascot/
├── server/
│   ├── ws_server.py        WebSocket server + REST event bridge (FastAPI)
│   └── tts_phoneme_export.py  espeak-ng phoneme timing bridge
├── frontend/
│   └── core/
│       ├── state_machine.js       idle/talking/listening/thinking + WS triggers
│       ├── emotion_transitions.js lerp transitions between 7 emotions
│       ├── expressions.js         f00-f06 slot mapping + 300ms fade
│       ├── phoneme_sync.js        phoneme-level mouth sync + amplitude fallback
│       ├── persistent_state.js    localStorage save/restore, 30min expiry
│       └── tts_sync.js            WebAudio AnalyserNode → ParamMouthOpenY
├── docs/
│   └── ARCHITECTURE.md    (this file)
└── tests/
    └── test_shared_smoke.py
```

---

## WebSocket protocol (v1)

All messages are JSON over `ws://host:8767/mascot`.

### Server → Client (broadcast)

| Type | Payload | Trigger |
|------|---------|---------|
| `CONNECTED` | `{"msg": str}` | On WS connect |
| `SET_STATE` | `{"state": str}` | POST /event/state |
| `SET_EXPRESSION` | `{"expression": str}` | POST /event/emotion |
| `TTS_EVENT` | `{"tts_type": str, "data": dict}` | POST /event/tts |
| `twitch_event` | `{"event": str, ...}` | POST /twitch-event |

### Valid states
`idle | talking | listening | thinking`

### Valid emotions (mapped to f-slots)
`neutral(f00) | happy(f01) | sad(f02) | angry(f03) | surprise(f04) | thinking(f05) | confused(f06)`

---

## REST API

| Endpoint | Method | Body | Effect |
|----------|--------|------|--------|
| `/health` | GET | — | `{"status":"ok","connected_clients":N}` |
| `/event/state` | POST | `{"state":str}` | Broadcast SET_STATE |
| `/event/emotion` | POST | `{"emotion":str}` | Broadcast SET_EXPRESSION |
| `/event/tts` | POST | `{"type":str,"data":{}}` | Broadcast TTS_EVENT |
| `/twitch-event` | POST | `{"event":str,...}` | Proxy Twitch events |

---

## State machine API (JS)

```javascript
// Global function (loaded after state_machine.js)
setMascotState('talking')          // triggers motion + expression
window.postMessage({ type: 'SET_STATE', state: 'listening' }, '*')

// Event listener for state changes
window.addEventListener('stateChanged', (e) => console.log(e.detail.state))
```

---

## Personality hooks — where repos plug in

```
┌─────────────────── shared/live2d_mascot/ ────────────────────┐
│  ws_server.py (protocol)                                      │
│  state_machine.js (transitions)                               │
│  expressions.js (f00-f06 slots)                               │
└────────────────────────────────────────────────────────────────┘
         │                              │
         ▼                              ▼
┌── Calliope.AI ──────────┐    ┌── Vesta ───────────────────┐
│ scripts/mascot_ws_server│    │ [path]/mascot_ws_server     │
│  .py (thin wrapper)     │    │  .py (thin wrapper)         │
│ frontend/live2d/app.js  │    │ frontend/vesta/app.js       │
│  → loads Hiyori model   │    │  → loads Minerva/custom     │
│ M3 scene pipeline       │    │  Inochi2D model             │
│ Aurora/Yokai chars      │    │  Minerva persona            │
│ Twitch/Discord bots     │    │  Vesta-specific events      │
└─────────────────────────┘    └────────────────────────────┘
```

### Calliope-specific overrides (in `scripts/mascot_ws_server.py`)
```python
_ws_core.LOG_FILE = "/tmp/calliope_mascot_ws.log"
_ws_core.app.title = "calliope-mascot-ws"
```

### Vesta-specific overrides (in vesta's thin wrapper)
```python
_ws_core.LOG_FILE = "/tmp/vesta_mascot_ws.log"
_ws_core.app.title = "vesta-mascot-ws"
```

---

## Coupling matrix

| Component | Shared | Calliope | Vesta |
|-----------|--------|----------|-------|
| WS protocol | ✅ | thin wrapper | thin wrapper |
| State machine | ✅ | uses as-is | uses as-is |
| Emotion slots | ✅ | uses as-is | uses as-is |
| Phoneme sync | ✅ | uses as-is | uses as-is |
| Mascot model (.moc3) | ❌ | Hiyori/Aurora | Minerva/custom |
| App init (app.js) | ❌ | Calliope-specific | Vesta-specific |
| Scene pipeline | ❌ | route_scene.py | N/A |
| Character roster | ❌ | Yokai chars | Vesta persona |

---

## Versioning

`shared/live2d_mascot` follows semver:
- **v1.0.0** (2026-05-18): initial extraction — WS server, state machine, 7 emotions, phoneme sync
- **v1.x**: minor additions (new event types, additional states)
- **v2.0**: breaking change in WS protocol requires consumer updates

Both repos pin to a git ref or copy version. No npm/pip publish required (single-machine deployment).

---

## Consumer import (Vesta)

```bash
# Symlink approach (preferred — single source of truth)
ln -s /home/nic/Scrivania/Calliope.AI/shared/live2d_mascot \
      /home/nic/Scrivania/Vesta/shared_live2d_mascot

# Python import in vesta thin wrapper
import sys
sys.path.insert(0, "/home/nic/Scrivania/Calliope.AI/shared")
from live2d_mascot.server.ws_server import app, main

# Frontend JS (HTML)
<script src="/path/to/shared_live2d/frontend/core/state_machine.js"></script>
```
