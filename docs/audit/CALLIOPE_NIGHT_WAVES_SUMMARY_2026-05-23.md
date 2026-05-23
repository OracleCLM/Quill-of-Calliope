# Calliope — Notte 2026-05-22/23 autonomy waves summary

**Per**: father-NM / operator nic
**Generated**: 2026-05-24 (orch-calliope opus autonomous)
**Mandate**: operator 2026-05-23 23:35 — full autonomy fino lunedi 7:30
**Branch state**: tutto merged + pushed a `origin/main`

---

## TL;DR

5 wave consecutive + 1 sprint chars-classify. **211/211 unit test PASS**, **43/43 browser test PASS**. Sprint C resta correttamente BLOCKED (operator-pending). Tutto su `origin/main`. Nessun blocker, nessuna escalation richiesta.

---

## Wave timeline

| Wave | Scope | Commit | Test | Status |
|---|---|---|---|---|
| **3 P0 fix pre-testing** | path-trav refine + chroma leak + discord memleak | `0bb58a8`, `788de86`, `9106cee` + merge `45b6094` | 17 unit | ✅ pushed |
| **VISION drift sync** | M3→M3.5 + M5/M6 anticipati (worker Sonnet) | `8ae6537` | n/a | ✅ pushed |
| **Sprint A — Dashboard quick-win** | vendor CDN + privacy badge + counters + empty-state + browser verify | `6eeda6f`, `71549b5`, `71e1339`, `98f7a71`, `15bdf60` + merge `b5db9c0` | 24 unit + 9 browser | ✅ pushed |
| **Sprint B — Dashboard tab** | snapshot endpoint + 5 panel + LLM toggle Q3 + Q6 Discord graceful + VISION drift correction + browser verify Q1/Q3/Q6/Q7 | `08d75d9`, `842305e`, `5c073ba`, `0c989d0`, `5196027` + merge `556425b` | 29 unit + 9 browser | ✅ pushed |
| **Chars classify draft** | operator-editable list 122 yaml | `b7204f1` | n/a | ✅ pushed |
| **Wave 7 — Browser smoke** | 25 test side-effect handler su 6 view restanti | `19e91d9` + merge `6340d7b` | 25 browser | ✅ pushed |
| **Wave 8 — P1 batch quick** | path-trav blend + SQLite WAL + prompt injection sanitize | `74f0b87`, `e453b99`, `80d671d` + merge `b4c6c3a` | 22 unit | ✅ pushed |
| **Wave 9 — P1 perf** | char_memory N+1 LIMIT + plot_arc chroma incremental | `8921c69`, `ebe534b` | 9 unit | ✅ pushed |

**Total**: 22 commit (16 atomic + 4 merge + 1 vision-drift + 1 chars-classify) → `d29edae..ebe534b` su origin/main.

---

## Audit finding chiusi

### P0 (3/3) — tutti chiusi pre-testing

| ID | Finding | Fix |
|---|---|---|
| P0 #1 | path-traversal `/api/scene/refine` | `_safe_read_scene_file` + 7 regression test |
| P0 #2 | ChromaDB connection leak | `@lru_cache(maxsize=1)` singleton (server + plot_arc) |
| P0 #3 | Discord rate-limit unbounded | `_cleanup_rate_state` TTL eviction + 6 test |

### P1 (5/12 critici chiusi)

| ID | Finding | Fix |
|---|---|---|
| P1 #4 | path-trav `/api/scene/blend` | `_safe_variants_path` tmp+scenes whitelist + filename pattern |
| P1 #5 | prompt injection LLM context | `_sanitize_user_prompt` + `_PROMPT_INJECTION_GUARD` |
| P1 #6 | README/VISION desync M0 | corretto wave Sonnet R-COPS-VISION-DRIFT |
| P1 #10 | N+1 char_memory entity overlap | `_ENTITY_OVERLAP_SCAN_LIMIT=500` + ORDER BY recency |
| P1 #11 | SQLite lock contention | `PRAGMA journal_mode=WAL` + `synchronous=NORMAL` |
| P1 #12 | ChromaDB upsert non-incremental | fingerprint cache `_arc_upsert_cache` + incremental upsert |

### P1 rimanenti (3) — deferred

| ID | Finding | Note |
|---|---|---|
| P1 #7 | Exception swallowing diffuso | scope grosso, deferred a sprint dedicato |
| P1 #8 | Test coverage 44.4% | richiede ~4-6h scrittura test estensivi |
| P1 #9 | server.py 678r monolith blueprint refactor | rischioso, richiede coordinamento con operator |

### P2/P3 — non toccati questa notte

VISION-SPEC-MISSING items, observability gaps (metrics, audit_trail) → Sprint C operator-blocked.

---

## Dashboard deliverable

### Sprint A — quick-win indipendenti dalle Q

- 🔒 **Privacy badge** in header — tooltip "local-only NO cloud upload", lista provider come ephemeral compute
- 📊 **Counters live** sidebar (Knowledge base) — chars 20/122 con amber warning
- 🌐 **Vendor CDN local** — 3 bundle (Live2D + PixiJS) in `static/js/vendor/` (777KB), zero traccia IP/UA
- 🎨 **Empty-state uniform** — `renderEmptyState()` helper + 3 refactor inline (scenes/messages/arc)

### Sprint B — tab "◈ Dashboard" landing (Q1=A)

5 pannelli grid:
1. **Stato sistema** — 4 daemon badge (Flask UP, LLM gateway/Mascot/ChromaDB)
2. **Conoscenza** — chars active/archive split (Q2 default), scene db/disk, arc, msg idx, lore
3. **Scorciatoie** — 4 azioni primarie (draft/refine/translate/arc)
4. **Tono sessione** (Q3) — provider attivo + bottone switch Ollama uncensored
5. **Discord** (Q6 code-prepared) — widget completo + CTA "configura token + avvia" graceful

Backend:
- `GET/POST /api/dashboard/llm_routing` — toggle profilo Cerebras ↔ Ollama uncensored
- `GET /api/dashboard/snapshot` — consolidato (daemons + counts + routing + activity placeholder)
- `GET /api/dashboard/counts` — Sprint A legacy preserved
- Perf budget: **<500ms warm verified runtime** (Q7 enforcement test)

JS:
- Polling 15s su panel attivo (NO WebSocket, Q7)
- Auto-show dashboard on DOMContentLoaded (Q1 landing)

---

## File generati per operator review

- `docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md` — 249r, 28 finding + 12 VISION gap
- `docs/audit/CALLIOPE_DASHBOARD_GAP_REVIEW_2026-05-22.md` — 213r technical findings
- `docs/audit/CALLIOPE_DASHBOARD_PROPOSAL_2026-05-22.md` — 318r debrief operator-friendly + 8 Q
- `docs/audit/CALLIOPE_CHARS_ACTIVE_ARCHIVE_DRAFT_2026-05-23.md` — 173r operator-editable list 122 char
- `docs/audit/CALLIOPE_NIGHT_WAVES_SUMMARY_2026-05-23.md` — questo file

---

## Pending operator decisions

| Q | Status | Wait for |
|---|---|---|
| Q2 chars criterion | pending | review draft + edit → spawn processing sprint |
| Q4 privacy lockdown attivo | pending | Sprint C unblock authorization |
| Q5 activity feed verbosity | pending | Sprint C unblock + audit_trail design |
| Operator review Dashboard live | pending | test funzionale operator-side |

---

## Sprint C — BLOCKED awaiting operator

Father mandate esplicito: NO esecuzione Sprint C senza operator-confirm Q4+Q5. Rispettato. Scope quando sbloccato:
- Privacy lockdown attivo (bottone Lock blocca runtime chiamate cloud)
- audit_trail SQLite table + ingest hook
- Activity feed UI toggle (on-demand / highlight / verbose)
- Wire al pannello "Attività recente" Dashboard

---

## Validation finale

```
unit suite:        211/211 PASS (53 nuovi durante la notte)
browser suite:      43/43 PASS (Sprint A + B + Wave 7)
pre-commit hooks:   tutti PASS su ogni commit
ruff lint:          0 issues
origin/main:        aggiornato a ebe534b
runtime browser:    privacy badge OK, counters OK, 0 external CDN req,
                    Q3 toggle OK, Q7 perf gate OK warm <500ms
```

---

## Recommended next actions (lunedi 7:30 cutoff)

**Per father, primo touchpoint operator**:
1. Notificare operator che ci sono **2 file da rivedere**: `CALLIOPE_DASHBOARD_PROPOSAL_2026-05-22.md` (8 Q decision) + `CALLIOPE_CHARS_ACTIVE_ARCHIVE_DRAFT_2026-05-23.md` (122 char checkbox edit)
2. Avviare Flask + browser per smoke test funzionale Dashboard live
3. Confermare Q4+Q5 per Sprint C unblock (privacy lockdown + activity feed)
4. Eventualmente dispatcheare:
   - Sprint C (3-4h post-confirm)
   - P1 #7 exception swallowing (scope medio, 2-3h)
   - P1 #8 test coverage generate_scene + discord_bot (4-6h estensivo)
   - P1 #9 server.py blueprint refactor (rischioso, richiede coordinamento)

Nessuna escalation in corso. Stato stable & pushed. Buona giornata operator.

— orch-calliope-opus
