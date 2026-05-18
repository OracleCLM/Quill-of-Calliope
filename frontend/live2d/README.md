# Quill of Calliope — Live2D Mascot Dashboard (Phase 1)

Mascot dashboard locale. PIXI.js + pixi-live2d-display (CDN). Placeholder model: Hiyori (Cubism 4).

## Setup

```bash
cd /home/nic/Scrivania/Quill_of_Calliope
python3 -m http.server 8080
```

Apri: `http://localhost:8080/frontend/live2d/`

## Files

| File | Description |
|------|-------------|
| `index.html` | HTML5 canvas + CDN scripts + UI overlay |
| `app.js` | PIXI app init, model load, window.mascotApp |
| `state_machine.js` | `setMascotState()` + WS/postMessage triggers |
| `tts_sync.js` | WebAudio lip-sync + stub polling :8767/tts-status |
| `style.css` | Dark theme, bottom control panel |

## State machine

```javascript
setMascotState('idle')      // Default breathing loop
setMascotState('talking')   // Mouth open + expression f01
setMascotState('listening') // Head tilt + expression f02
setMascotState('thinking')  // Look-up + expression f03

// External triggers
window.postMessage({ type: 'SET_STATE', state: 'talking' }, '*')
// or via WebSocket ws://localhost:8767 (Phase-2 backend)
```

## Lip-sync

```javascript
// Attach to <audio> element for amplitude-driven mouth sync
const sync = attachToAudio(document.getElementById('my-audio'));
sync.start();  // begins requestAnimationFrame loop
sync.stop();   // resets mouth, cancels loop
```

## Phase-2 roadmap

- `scripts/llm_gateway_http.py` endpoint `/speak` → stream TTS WAV
- WebSocket server at `:8767` → real-time state push
- Replace Hiyori placeholder with custom Calliope mascot model (.moc3)
- Real lip-sync: WAV phoneme timing → keyframe animation

## Browser requirements

Chrome 90+ / Firefox 88+ / Edge 90+ (WebAudio API + WebSocket required)


## Phase-3 E2E demo

```bash
# Start all services
bash scripts/start_llm_gateway_http.sh
bash scripts/start_mascot_ws.sh
# Run E2E demo
python3 scripts/run_e2e_demo.py
```
