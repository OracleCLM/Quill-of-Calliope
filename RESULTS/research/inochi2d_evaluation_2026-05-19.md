# Inochi2D Evaluation Report — 2026-05-19

**Sprint**: R-CALLIOPE-G06-AURORA-RENAME-INOCHI2D-EVAL Phase 2
**Evaluator**: sonnet2-calliope
**Status**: EVAL-ONLY — NO adoption commit (father+operator decision gate)

---

## 1. Feature Matrix

| Feature | Live2D Cubism | Inochi2D | Nijigenerate |
|---------|--------------|----------|--------------|
| License | Commercial (fee for non-personal) | BSD-2-Clause | BSD-2-Clause |
| Rigging tool | Cubism Editor | Inochi Creator (v0.8.6 Flatpak) | nijigenerate (nightly/weekly Flatpak) |
| Runtime | Cubism SDK (commercial) | D lang lib + C FFI | nijilive (fork) |
| Web/JS runtime | pixi-live2d-display | No official JS SDK | No official JS SDK |
| VMC blendshapes | Via VTube Studio | Yes — Session supports VMC protocol | Via nijiexpose |
| Face tracking | Via VTS | Inochi Session (v0.8.7) | nijiexpose |
| Asset format | .moc3 + .model3.json | .inp puppet format | .nijilive format |
| PSD import | Cubism Editor | Inochi Creator (PSD layers → mesh) | nijigenerate (PSD layers) |
| Re-rig needed (from Live2D) | N/A | YES — format incompatible | YES — format incompatible |
| WebSocket emotion sync | Via custom WS | VMC over WS (Session) | Via nijiexpose WS |
| Physics | ✅ full | ✅ | ✅ |
| Linux support | ✅ | ✅ Flatpak + source | ✅ Flatpak experimental |
| Upstream activity | Active | Less active (2026 per Oreate AI) | Community-maintained fork, more active |
| Open source | No (SDK closed) | Yes (D lang, BSD-2) | Yes (BSD-2 fork) |

---

## 2. License Analysis

**Calliope target license**: MIT (planned)

- **Live2D Cubism**: Production Free fee structure applies for commercial or "non-personal" use. For a private local tool (NM-only, single user), free tier may apply but license terms are ambiguous for AI-augmented RP tools. Risk: if Calliope grows to multi-user/commercial, Cubism license becomes a liability.
- **Inochi2D BSD-2**: Fully compatible with MIT-target. No royalty, no attribution required in binary. Safe for any downstream.
- **Nijigenerate BSD-2**: Same as Inochi2D. Fork from v0.8, community-maintained (github.com/nijigenerate).

**Verdict**: Inochi2D / Nijigenerate are license-clean for Calliope MIT-target. Live2D Cubism is tolerable at current scope but carries future risk.

---

## 3. NM Hardware Installation Test

**Flatpak availability** (verified on NM 2026-05-19):
```
Inochi Session    com.inochi2d.inochi-session  0.8.7  stable  flathub  ✅
Inochi Creator    com.inochi2d.inochi-creator  0.8.6  stable  flathub  ✅
nijigenerate      (no stable flatpak)                                  ❌ nightly only
```

**Install test**: Flatpak packages available. Install would be `flatpak install flathub com.inochi2d.inochi-creator`. NOT installed in this sprint (eval-only, no global install per anti-AP mandate).

---

## 4. Asset Migration Effort

Current Calliope mascot:
- `shared/live2d_mascot/models/calliope/calliope.model3.json` — placeholder, no real .moc3 asset yet
- No actual Cubism-rigged asset exists (Sprint 5 TODO)

**If migrating to Inochi2D**:
- Existing placeholder: 0 effort (no real asset to migrate)
- New rigging from PSD: 8-20h (moderate complexity avatar, face + body deformation)
- Runtime integration: replace pixi-live2d-display CDN with Inochi2D C FFI or web WASM wrapper (~1-2 sprint)
- Emotion sync: VMC over WS is closer to Phase-3 mascot_ws_server.py pattern — lower glue code

**Estimated total migration effort** (if adopted at Sprint 5): ~2-3 sprints (rigging + runtime + integration).

---

## 5. Recommendation

**DEFER** — with strong note to revisit at Sprint 5 (mascot asset creation decision point).

**Rationale**:
1. No real Cubism asset exists yet — switching cost is near-zero now, but the pixi-live2d-display CDN JS runtime is already wired in shell.html (Sprint 3). Ripping it out requires Sprint 5 scope.
2. Inochi2D upstream activity has slowed (2026); Nijigenerate is the active fork but no stable Flatpak.
3. Current pixi-live2d-display stack is functional for placeholder phase. Re-evaluate at Sprint 5 when real mascot asset is commissioned.
4. License risk from Live2D Cubism is real but non-blocking at current NM-single-user scope.

**Trigger for re-evaluation**: if Calliope expands beyond NM single-user OR when real mascot asset (.moc3) is commissioned — at that point Inochi2D/Nijigenerate is the preferred path (BSD-2 + VMC WS align with Phase-3 emotion sync architecture).

---

## 6. Appendix — Sources

- inochi2d.com — official site, feature overview
- github.com/Inochi2D/inochi2d — BSD-2, D lang, C FFI
- github.com/nijigenerate/nijigenerate — BSD-2 fork, VTubing focus
- github.com/Inochi2D/inochi-session — v0.8.7 Flatpak, VMC support
- `flatpak search inochi` — NM verified 2026-05-19
- Sprint proposal: `SPRINT_PROPOSAL_R-CALLIOPE-G06-AURORA-RENAME-INOCHI2D-EVAL.md`
