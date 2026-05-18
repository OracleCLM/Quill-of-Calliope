# Live2D Mascot Frontend Core

Repo-agnostic JavaScript modules. Load via `<script>` tags in any project.

## Files

| File | Purpose |
|------|---------|
| `core/state_machine.js` | `setMascotState(s)` — idle/talking/listening/thinking |
| `core/emotion_transitions.js` | Lerp between 7 emotion expressions |
| `core/expressions.js` | f00-f06 slot map + 300ms fade |
| `core/phoneme_sync.js` | Phoneme-level mouth sync + amplitude fallback |
| `core/persistent_state.js` | localStorage mascot state, 30min expiry |
| `core/tts_sync.js` | WebAudio AnalyserNode → ParamMouthOpenY |

## Usage

```html
<!-- After PIXI + pixi-live2d-display CDN -->
<script src="path/to/shared/live2d_mascot/frontend/core/state_machine.js"></script>
<script src="path/to/shared/live2d_mascot/frontend/core/tts_sync.js"></script>
<!-- etc. -->
```

Requires `window.mascotApp = { app, model }` to be set by project-specific `app.js`.
