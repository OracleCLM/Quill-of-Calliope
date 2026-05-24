# Reboot snapshot — orch-calliope-opus

**Timestamp**: 2026-05-24T02:42 Europe/Rome
**Trigger**: father REBOOT PROTOCOL — NVIDIA driver mismatch kernel 580.142 vs userspace 580.159 (blocca Blender)
**Orch**: orch-calliope-opus (Claude Opus 4.7, autonomous session)
**Branch state**: `main` synced with `origin/main` at `19cff69`. Working tree clean (untracked = local-only artifacts, all in .gitignore).

---

## 1. Sprint in flight

**Nessuno in flight**. Sprint C completato + merged + pushed prima del reboot mandate. Stato pulito.

### Sprint just-closed (questa sessione autonoma)

| Sprint | Commit | Stato |
|---|---|---|
| Sprint C1 — audit_trail SQLite schema | `45de57f` | ✅ done + pushed |
| Sprint C2 — write-event ingest hooks (10 site) | `4925abf` | ✅ done + pushed |
| Sprint C3 — `/api/dashboard/activity` endpoint | `39d038f` | ✅ done + pushed |
| Sprint C4 — Dashboard "Attività recente" panel + 3-mode toggle | `4bd3022` | ✅ done + pushed |
| Sprint C5 — Cloud warning per-call modal (Q4 soft) | `6ea7b73` | ✅ done + pushed |
| Sprint C6 — Browser verify Sprint C + audit init wiring fix | `7a5f3d4` | ✅ done + pushed |
| Sprint C merge → main | `19cff69` | ✅ pushed origin/main |

### Earlier this session (pre-Sprint-C, già pushed)

- Wave 9 perf: P1 #10 char_memory N+1 LIMIT (`8921c69`), P1 #12 plot_arc chroma incremental (`ebe534b`)
- Wave 8 P1 quick: path-trav blend + WAL + prompt injection (3 commit)
- Wave 7 browser smoke: 25 test 6 view (`19e91d9`)
- Sprint B + chars-classify + Sprint A: già loggati in `docs/audit/CALLIOPE_NIGHT_WAVES_SUMMARY_2026-05-23.md`

### Queue position

DISPATCH_QUEUE non gestita da questo orch (self-execute mode). Nessun lock pendente, nessun entry orphan.

---

## 2. Prossimi sprint candidati post-reboot

Backlog operator-pending + P1 deferred. Ordine consigliato per ROI:

### Sprint D1 — Operator review files (NO code, ~30min)

**Trigger**: operator manda feedback su:
- `docs/audit/CALLIOPE_DASHBOARD_PROPOSAL_2026-05-22.md` (8 Q operator-decision)
- `docs/audit/CALLIOPE_CHARS_ACTIVE_ARCHIVE_DRAFT_2026-05-23.md` (122 char checkbox edit)

**Output post-trigger**: spawn sprint processing che applica le decisioni al codice.

### Sprint D2 — Smoke test funzionale Dashboard live (~15-30min operator)

Operator avvia Flask + browser → test workflow 5-step Messages→Scenes→Continue→Refine→Translate sul Dashboard tab nuovo.

Bug eventuali → mini-fix sprint dispatch.

### Sprint D3 — P1 #7 exception swallowing diffuso (~2-3h)

Audit ref: `docs/audit/CALLIOPE_DEEP_REVIEW_2026-05-22.md` §2 P1 #7. Scope: 19+ bare `except Exception:` in `scripts/discord_persona_binder.py`, `scripts/discord_bot.py`, `app/calliope_shell/narrative_state.py`. Narrow exception types + `log.exception()` per preservare traceback. Re-raise selettivo.

### Sprint D4 — P1 #8 test coverage generate_scene + discord_bot (~4-6h)

Coverage attuale 44.4%. `scripts/generate_scene.py` 0% (244r main function), `scripts/discord_bot.py` 47%, `scripts/build_chromadb_index.py` core untested. Sprint estensivo richiede fixture mocks LLM gateway + Discord client.

### Sprint D5 — P1 #9 server.py blueprint refactor (~6-8h, RISCHIOSO)

`app/calliope_shell/server.py` ora ~1100 righe dopo Sprint A+B+C. 35+ route handler in unica `create_app()` factory. Refactor in Flask Blueprints (`mascot_routes.py`, `translate_routes.py`, `memory_routes.py`, `scene_routes.py`, `arc_routes.py`, `dashboard_routes.py`). Coordinazione operator consigliata — touch tutti gli endpoint.

---

## 3. File edits non-commit pending

**Nessuno**. `git status -s` mostra solo file untracked che sono:
- `.claude/agents/`, `.claude/skills/` — local CLI tooling, gitignored
- `calliope_discord_snippet.txt` — local artifact, gitignored
- `data/char_memory.db`, `data/chromadb/`, `data/discord_persona_config.db` — runtime DB, gitignored
- `graphify-out/` — graphify hook output, gitignored

Tutti expected, nessun edit code-side perso.

---

## 4. Decision context per riprendere veloce

### Operator decisions implementate (recap)

| Q | Decisione | Implementazione |
|---|---|---|
| Q1 | Dashboard tab prima voce | ✅ Sprint B2 (`842305e`) |
| Q2 | chars criterion | ⏸ pending operator review `CALLIOPE_CHARS_ACTIVE_ARCHIVE_DRAFT_2026-05-23.md` |
| Q3 | LLM toggle visibile + switch Ollama | ✅ Sprint B3 (`5c073ba`) |
| Q4 | privacy soft warning per-call | ✅ Sprint C5 (`6ea7b73`), NO hard Lock |
| Q5 | activity feed write-only 3-mode | ✅ Sprint C1-C4 |
| Q6 | Discord code-prepared graceful | ✅ Sprint B2 |
| Q7 | <500ms warm + polling 15s | ✅ Sprint B1+B2 |
| Q8 | vendor CDN local | ✅ Sprint A1 |

### Daemon dependencies per testing Dashboard

Per smoke funzionale operator deve avviare:
- Flask shell: `FLASK_APP=app.calliope_shell.server python -m flask run --port 5000` (o desktop launcher)
- LLM gateway: `scripts/start_all_calliope_daemons.sh` (avvia gateway 8766 + mascot WS 8767)
- ChromaDB: già su disco, no daemon
- Discord bot: SKIP — bot non attivato (token non configurato, Q6 graceful)

### File chiave per ripresa

- `docs/audit/CALLIOPE_DASHBOARD_PROPOSAL_2026-05-22.md` — 8 Q operator-decision
- `docs/audit/CALLIOPE_CHARS_ACTIVE_ARCHIVE_DRAFT_2026-05-23.md` — 122 char checkbox edit operator
- `docs/audit/CALLIOPE_NIGHT_WAVES_SUMMARY_2026-05-23.md` — recap waves precedenti
- `app/calliope_shell/audit_trail.py` — modulo nuovo Sprint C1, EVENT_KINDS/HIGHLIGHT_KINDS
- `app/calliope_shell/templates/shell.html` — Dashboard tab + 5 panel + cloud-warn modal + activity feed

### Test runtime quick verify post-reboot

```bash
# Unit suite (~50s)
python -m pytest tests/unit/ -q

# Browser suite (richiede Flask up)
(FLASK_APP=app.calliope_shell.server python -m flask run --port 5005 &) && \
  sleep 5 && \
  FLASK_TEST_URL=http://127.0.0.1:5005/ python -m pytest tests/browser/ -v
```

Expected: 268/268 unit + 57 browser PASS.

---

## 5. Costo + token sessione corrente

**Stima approssimata** (orch self-execute, no precise telemetry):

- **Token totali stimati**: ~250-300k input + ~80-120k output (sessione lunga multi-wave)
- **Costo Opus 4.7** stimato: ~$8-15 input + ~$6-12 output = **~$15-25 sessione cumulative**

Modello primario: Claude Opus 4.7 (orchestrator self-execute, no worker spawn dopo Sprint A audit). Tre worker Explore lanciati durante deep-review iniziale (Sonnet 4.6, ~143k token aggregated, costo trascurabile).

**Cost-effectiveness verdict**: alta. 31 commit pushed + 268 test + 57 browser test + Sprint A+B+C completi + 5 audit doc operator-friendly = ratio output/costo solido.

---

## 6. Branch state finale

```
local:   main → 19cff69 (clean)
origin:  main → 19cff69 (synced)
ahead:   0
behind:  0

Recent commits on main (top of stack):
  19cff69  merge: Sprint C — privacy warning per-call + audit_trail + activity feed
  7a5f3d4  test(browser): Sprint C end-to-end verify + audit init wiring
  6ea7b73  feat(privacy): cloud warning per-call modal (Sprint C5, Q4 soft)
  4bd3022  feat(ui): Dashboard 'Attività recente' panel + 3-mode toggle (Sprint C4)
  39d038f  feat(api): /api/dashboard/activity endpoint + snapshot wire (Sprint C3)
  4925abf  feat(audit): write-event ingest hooks across modules (Sprint C2)
  45de57f  feat(audit): audit_trail SQLite schema (Sprint C1, Q5 write-only)
  4bd1aa1  docs(audit): night waves summary 2026-05-23 — father/operator ping
```

Branch fix/* e feat/* di passato (3 P0 fix, Sprint A, Sprint B, Wave 7-9, Sprint C) tutti merged a main. Da rimuovere a discrezione operator post-reboot via `git branch -d <branch>` (non blocca).

---

## 7. Resume protocol post-reboot

1. Operator riavvia macchina, kernel module nvidia 580.159 ricaricato
2. Operator spawn nuova sessione `orch-calliope-opus` (o riprende esistente se persistent)
3. Orch legge **questo file** + `docs/audit/CALLIOPE_NIGHT_WAVES_SUMMARY_2026-05-23.md` per context restore
4. Verifica branch state + test suite (comandi §4)
5. Standing-by per operator input su:
   - Smoke test Dashboard live (Path B di proposal)
   - Q2 chars criterion review
   - Sprint D3 P1 #7 exception swallowing dispatch
   - Altro

**Status pre-reboot**: stable, safe, no work-in-progress lost.

— orch-calliope-opus, 2026-05-24T02:42
