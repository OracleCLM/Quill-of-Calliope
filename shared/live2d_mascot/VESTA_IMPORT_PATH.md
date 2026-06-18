# Vesta Import Path — Live2D Shared Infra

**DO NOT MODIFY VESTA REPO DIRECTLY** — this doc is for orch-vesta reference.
Operator-authorized cross-repo import (sprint R-CALLIOPE-LIVE2D-INFRA-EXTRACT-FOR-VESTA-REUSE).

## Option 1: Symlink (recommended)

```bash
# From Vesta repo root
ln -s /home/nic/Scrivania/Quill_of_Calliope/shared/live2d_mascot \
      ./shared/live2d_mascot
```

Then in Vesta's mascot server script:
```python
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "shared"))
from live2d_mascot.server.ws_server import app, main

# Vesta overrides
import live2d_mascot.server.ws_server as _core
_core.LOG_FILE = "/tmp/vesta_mascot_ws.log"
_core.app.title = "vesta-mascot-ws"
```

## Option 2: sys.path absolute (dev/test only)

```python
import sys
sys.path.insert(0, "/home/nic/Scrivania/Quill_of_Calliope/shared")
from live2d_mascot.server.ws_server import app, main
```

## Frontend JS (HTML)

```html
<!-- Absolute path (NM-local dev) -->
<script src="/home/nic/Scrivania/Quill_of_Calliope/shared/live2d_mascot/frontend/core/state_machine.js"></script>

<!-- Relative path via symlink (recommended) -->
<script src="../shared/live2d_mascot/frontend/core/state_machine.js"></script>
```

## Mascot model — Mao (shared shippable default)

The shared package now ships a default Live2D model: **Mao** (Live2D official
sample model, Free Material License — see `models/mao/README.md`). Vesta loads it
through the same shared shell by pointing `MASCOT_CONFIG` at the shared model path:

```html
<script id="mascot-config">
  window.MASCOT_CONFIG = {
    // via the recommended symlink (../shared/live2d_mascot → shared package)
    modelUrl: '../shared/live2d_mascot/models/mao/Mao.model3.json',
    canvasId: 'live2d-canvas',
    idleMotion: 'Idle',
    // optional: override emotion→expression slots for a different model
    // expressionMap: { neutral: {slot:'exp_01'}, joy: {slot:'exp_02'}, ... },
  };
</script>
```

`createMascotRenderer(window.MASCOT_CONFIG)` then mounts Mao with the shared
renderer (idle motion + auto breath/blink fallback for motionless models).
Mao's expressions are `exp_01..exp_08`; motions are `Idle` / `TapBody`.

> Mao is the ONLY shippable model. `models/koko/` and `models/tingyun/` are
> license-restricted dev-reference models (gitignored, NM-local only) for
> aesthetic evaluation and must never ship.

## Inochi2D convergence note

Vesta WAVE-M3-B is evaluating Inochi2D (alternative to Live2D Cubism).
The shared WS protocol and state machine JS are engine-agnostic — they broadcast
`SET_STATE` / `SET_EXPRESSION` events that any renderer can consume.

Replace `window.mascotApp.model.motion(...)` calls in `state_machine.js` with
Inochi2D equivalent when Vesta adopts it. The protocol layer stays shared.

## Version pinned

`shared/live2d_mascot` v1.0.0 (2026-05-18)
See `shared/live2d_mascot/docs/ARCHITECTURE.md` for full API.
