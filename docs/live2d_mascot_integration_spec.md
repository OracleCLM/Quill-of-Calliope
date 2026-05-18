# Live2D Mascot Integration Spec — Quill of Calliope

**Status**: PHASE-2 IMPL DONE (2026-05-17) — Phase-3 pending
**Version**: v1.5
**Created**: 2026-05-17 | **Target milestone**: M4-M5

## Phase-1 status (DONE — sprint R-CALLIOPE-LIVE2D-IMPL-PHASE1)

- `frontend/live2d/index.html` — PIXI.js + pixi-live2d-display CDN, Hiyori placeholder
- `frontend/live2d/app.js` — model load, centering, `window.mascotApp`
- `frontend/live2d/state_machine.js` — idle/talking/listening/thinking + WS + postMessage
- `frontend/live2d/tts_sync.js` — WebAudio amplitude lip-sync + stub polling :8767
- `frontend/live2d/style.css` — dark theme UI overlay
- `tests/live2d/test_frontend_structure.py` — 6 smoke tests PASS
- Serve: `python3 -m http.server 8080` → `http://localhost:8080/frontend/live2d/`


## Phase-2 status (DONE — sprint R-CALLIOPE-LIVE2D-PHASE2)

- `frontend/live2d/expressions.js` — 7-emotion library (joy/sad/anger/surprise/neutral/thinking/confused), f00-f06 slots, 300ms fade
- `frontend/live2d/emotion_transitions.js` — transition matrix 6 from→to combos, PIXI.Ticker lerp / rAF fallback
- `frontend/live2d/phoneme_sync.js` — phoneme-level mouth sync, setTimeout scheduling, amplitude fallback
- `frontend/live2d/persistent_state.js` — localStorage save/restore, 30min expiry
- `scripts/tts_phoneme_export.py` — espeak-ng IPA → phoneme timing JSON (graceful if espeak absent)
- `tests/live2d/test_phase2_structure.py` — 17 tests PASS

## Phase-3 roadmap

- Replace PIXI-Live2D-Display with Cubism SDK Web (.moc3 custom model)
- WebSocket :8767 real-time push from Python orchestrator
- Custom Calliope mascot design (operator decision: separate from Aurora canon char)
- Vite bundle (move off CDN)
- A/B expression testing per scene type (analytics)


### Phoneme Pipeline — REAL (2026-05-17)
* espeak-ng v1.51 installed at `/usr/bin/espeak-ng`, resolving blocker (2026-05-17)
* `tts_phoneme_export.py` now fully functional with real IPA phoneme extraction
* IPA vowel map extended with ɐ, ə, ɜ, ɑ, ʌ, ɒ for better espeak-ng coverage
* Sprint: R-CALLIOPE-PHONEME-SYNC-VERIFY-WITH-REAL-ESPEAK

## Phase-3 status (DONE — sprint R-CALLIOPE-WEBSOCKET-BACKEND-PHASE3)
* WebSocket server: `mascot_ws_server.py` at `ws://localhost:8767/mascot` with multi-client broadcast
* REST triggers: `POST /event/state`, `/event/emotion`, `/event/tts`
* Frontend `state_machine.js` auto-connects (Phase-1 done), no modifications needed
* Tests: 9/9 PASS (TestClient sync WS tests)
* Start: `bash scripts/start_mascot_ws.sh`
* Completed: 2026-05-17

## Phase-3 E2E (DONE — sprint R-CALLIOPE-E2E-INTEGRATION-TEST-PHASE3)
* Test suite `test_e2e_integration_phase3.py`: 8 tests PASS cross-component (WS + LLM gateway + Ollama + TTS + phoneme)
* Demo script `run_e2e_demo.py`: 3-scene chain gen → TTS phoneme → WS broadcast cycle
* Playwright: gracefully skipped (not installed), infrastructure in place for future CI
* Total: 198 tests PASS, 2 skipped (playwright)
* Date: 2026-05-18

## Phase-2 roadmap (archived)

- Backend `/speak` endpoint (FastAPI/aiohttp) wire-up
- WebSocket `:8767` real-time state push from Python
- Replace Hiyori with custom Calliope mascot (.moc3 Cubism 4)
- Real phoneme timing from WAV → keyframe lip-sync
- Bundle with Vite (move off CDN for production)

---

## 1. Mascot persona (operator decision pending)

Two candidates:
- **Aurora** (existing RP char, Okami-mimi queen fox) — familiar, but canonical char risks drift
- **"Calliope"** (new original mascot) — clean slate, no lore conflicts, custom visual design

**Recommendation**: Custom Calliope mascot (avoid canon Aurora confusion). Operator decides at M4 kickoff.

---

## 2. Live2D SDK choice

| SDK | Pros | Cons | Recommendation |
|-----|------|------|----|
| **Cubism SDK Web** (official) | Full feature set, animations, physics | Requires Cubism model format (.moc3), heavier bundle | For production |
| **PIXI-Live2D-Display** | Lightweight, PIXI.js integration, open-source | Less official support | For MVP/prototype |
| **live2d-viewer-web** | Zero-config demo tool | No programmatic API | Dev preview only |

**Recommended path**: PIXI-Live2D-Display for MVP prototype → migrate to Cubism SDK Web if quality demands increase.

---

## 3. Integration points

### 3a. TTS → Lip-sync

```
tts_speak_bilingual(scene_text) → WAV bytes
    │
    ▼
WAV analysis → phoneme timing extraction (CMU Pronouncing Dict or WebAudio API)
    │
    ▼
Live2D mouth parameter (PARAM_MOUTH_OPEN_Y) → keyframe animation
```

- **Tool**: `pydub` + zero-crossing analysis OR WebAudio `AnalyserNode` (real-time)
- **Precision tier**: approximate (open/close sync) — NOT phoneme-perfect for MVP
- **Latency target**: <100ms mouth-open lag after audio start

### 3b. Scene mood → Expression

```
route_scene(scene_type, nsfw_score) → tier + rationale
    │
    ▼
scene_type → expression_map → Live2D expression parameter
```

Expression mapping:
| scene_type | Expression | Parameters |
|------------|------------|-----------|
| `action_combat` | Determined | PARAM_BROW_L/R_Y=-1, PARAM_EYE_OPEN=1.2 |
| `lore_exposition` | Thoughtful | PARAM_BROW_L_ANGLE=0.5 |
| `romantic_fade_to_black` | Soft | PARAM_MOUTH_FORM=0.5, PARAM_EYE_OPEN=0.8 |
| `ooc_meta` | Casual/idle | All neutral |
| `character_death` | Sad | PARAM_BROW_L/R_Y=1, PARAM_EYE_OPEN=0.6 |
| `climax_rare` | Intense | PARAM_EYE_OPEN=1.5 |

### 3c. Idle state

- Loop idle animation (breathing, hair movement) when no scene active
- Subtle random blinks every 3-7s
- Trigger "listening" pose when scene gen request incoming

---

## 4. Dashboard frontend stack

**Decision deferred to operator** — options:

| Stack | Bundle size | Dev speed | Recommendation |
|-------|------------|-----------|----------------|
| **Vue 3 + Vite** | Small | Fast | Recommended |
| React + Vite | Medium | Fast | OK |
| Vanilla JS + WebComponents | Minimal | Slow | For minimal deps |

**Common**: PIXI.js v7 (Live2D renderer), WebSocket to Python backend, Tailwind CSS.

**Deployment**: localhost:5173 (Vite dev) or localhost:8080 (prod build) on NM only.

---

## 5. Data flow diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Calliope Dashboard (Browser)          │
│                                                         │
│  ┌─────────────┐    ┌──────────────┐    ┌───────────┐  │
│  │ Scene input │───▶│ WebSocket API│───▶│ Live2D    │  │
│  │ (text/CLI)  │    │  /generate   │    │ Mascot    │  │
│  └─────────────┘    └──────────────┘    │ (PIXI.js) │  │
│                            │            └───────────┘  │
│                            │ WAV + metadata             │
│                            ▼                           │
│                     ┌──────────────┐                   │
│                     │ AudioContext │ lip-sync           │
│                     │ Web Audio API│──────────────────▶│
│                     └──────────────┘                   │
└─────────────────────────────────────────────────────────┘
                            ▲
                            │ WebSocket
┌───────────────────────────┴──────────────────────────┐
│                  Python Backend (FastAPI/aiohttp)     │
│                                                      │
│  route_scene() ──▶ LLM gateway ──▶ scene text       │
│  tts_speak_bilingual() ──▶ WAV bytes                 │
│  ChromaDB retrieval ──▶ context/lore                 │
└──────────────────────────────────────────────────────┘
```

---

## 6. Animation library (mascot states)

| State | Trigger | Animation |
|-------|---------|-----------|
| `idle` | No active scene | Breathing loop + random blink |
| `listening` | Scene request received | Head tilt + ear perk (Aurora) |
| `talking` | TTS playing | Lip-sync + WAV-driven mouth |
| `thinking` | LLM inference in progress | Swirling eyes / spinner overlay |
| `happy` | Scene success | Tail wag + smile |
| `surprised` | BLOCK triggered | Jump back expression |

---

## 7. Effort estimate

| Component | Effort | Dependency |
|-----------|--------|------------|
| Mascot model creation (Cubism) | XL (8-16h) | Artist or VTuber asset |
| PIXI-Live2D setup + idle | M (3-5h) | Mascot model |
| TTS → lip-sync approximation | M (4-6h) | tts_speak_bilingual |
| scene_type → expression mapping | S (2h) | route_scene |
| Dashboard frontend scaffold | L (6-10h) | Stack decision |
| WebSocket API backend | M (3-5h) | FastAPI |
| Full integration + testing | L (8-12h) | All above |
| **Total** | **~34-54h** | |

**MVP shortcut** (operator option): Skip custom mascot model, use a CC0 VTuber model from
Booth/VRoid Hub → reduces XL component to S (~2h). Verify license compatibility.

---

## 8. Privacy boundaries (inherited from llm_routing.md)

- Mascot runs 100% local (NM only), no cloud upload
- TTS WAV files: temp only, never persisted by dashboard
- Scene text: sent to LLM tiers per routing policy (sensitive → Ollama local)
- No biometrics/PII in mascot data flow

---

## 9. Next steps (operator decision required)

- [ ] Confirm mascot persona (Aurora vs Calliope original)
- [ ] Confirm frontend stack (Vue 3 recommended)
- [ ] Source or commission mascot model (Cubism .moc3)
- [ ] Confirm M4 sprint allocation for dashboard scaffold
