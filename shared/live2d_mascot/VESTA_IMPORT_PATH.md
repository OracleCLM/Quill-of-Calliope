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

## Inochi2D convergence note

Vesta WAVE-M3-B is evaluating Inochi2D (alternative to Live2D Cubism).
The shared WS protocol and state machine JS are engine-agnostic — they broadcast
`SET_STATE` / `SET_EXPRESSION` events that any renderer can consume.

Replace `window.mascotApp.model.motion(...)` calls in `state_machine.js` with
Inochi2D equivalent when Vesta adopts it. The protocol layer stays shared.

## Version pinned

`shared/live2d_mascot` v1.0.0 (2026-05-18)
See `shared/live2d_mascot/docs/ARCHITECTURE.md` for full API.
