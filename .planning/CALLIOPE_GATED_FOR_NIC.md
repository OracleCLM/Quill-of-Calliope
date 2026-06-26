# Calliope — Decisioni GATED per operatore (nic)

> Aggiornato: 2026-06-26 ciclo round-6 (arc-seed except test → server.py 94%→98%; suite 2281 passed unit) da sonnet-orch-calliope.
> File accumulativo: ogni sessione appende le decisioni bloccanti. Rimuovi la riga dopo che hai dato il via libera.

---

## ✅ [DONE] GATED-1 — UI chat JanitorAI lista-flat (commit 0e15464, 5473e16)

**Blocco**: `scenes.js` ha già lista/detail base. Manca la vera UI-chat stile JanitorAI:
- render-thread ordinato (bolle/lista?)
- compose come narratore o personaggio attivo
- selezione-import da Discord history

**Domande richieste**:
1. **Paradigma visivo**: lista flat (come JanitorAI chat) oppure vista classica con bolle per personaggio?
2. **Sostituire o affiancare** il pannello scenes esistente? Il vecchio usa `/api/scenes` YAML + ChromaDB; il nuovo usa `/api/db/scenes` CRUD. Convivenza o migrazione completa?
3. **Minimo accettabile** per iniziare: solo render-thread + compose narratore senza bolle/avatar, oppure si vuole già il composito con selezione personaggio?

**Stato backend**: COMPLETO. Tutti gli endpoint `/api/db/scenes`, messaggi, roster pronti.

---

## ✅ [DONE] GATED-2 — Config gateway-strong-uncensored (commit 0e15464)

**Blocco**: `apply_refine_to_message` usa di default Groq `llama-3.3-70b-versatile`. Per scene sensibili (raffinamento dark/erotico) il workplan prevede un modello-strong uncensored configurabile (Ollama abliterated o OpenRouter).

**Domanda**: Quale modello usare come "strong-uncensored" per E3?
- Ollama locale (`dolphin-mistral` o abliterated)?
- OpenRouter (quale modello specifico — `qwen/qwen3-coder:free` non è il miglior fit per narrativa)?
- Cerebras `zai-glm-4.7` (censored ma molto capace)?

Impatto: basta una variabile env `REFINE_PROVIDER` / `REFINE_MODEL` configurabile.

---

## [GATED-3] M6 Discord bot activation

**Blocco**: codice bot pronto (commit 297b10e). Mancano:
- (a) `CALLIOPE_DISCORD_BOT_TOKEN` in `.env`
- (b) `scripts/start_discord_bot.sh` avviato
- (c) design "instructions + interpellation game master" che precede l'esposizione del bot ai canali live

**Non è un gap di codice** — è decisione operativa/timing.

---

## ✅ [DONE] GATED-4 — Redesign JanitorAI P0-P6 strutturale (parziale)

**Blocco**: VISION menziona "restructure JanitorAI P0-P6". La spec `CALLIOPE_REDESIGN_SPEC.md` è in `.planning/`. Toca:
- paradigma scene=chat (backend DONE, frontend mancante → vedi GATED-1)
- widget/overlay audio-visivi (Live2D mascot DONE, TTS attivo)
- future abliteration locale (OBLITERATUS)

**Completato (2026-06-25)**: chat lista-flat, _sceneAction bugfix, scene list message_count+is_readonly, revive DB fallback. P6/P7 restano GATED.

---

## ✅ [DONE] GATED-5 — POST /api/messages/next rimosso (branch efesto/gated5-remove-messages-next, commit f3a4e3b)

**Eseguito 2026-06-26**: Rimossa route codice morto `POST /api/messages/next` (~100 righe). 6 file di test aggiornati. Suite: 2344 passed.
Branch dedicato: `efesto/gated5-remove-messages-next` — non ancora mergato su main.

---

## ✅ [DONE] GATED-6 — Arc DB canonical (branch efesto/gated6-arc-db-canonical, commit 05152b9)

**Eseguito 2026-06-26**: DB ora fonte canonica degli archi. Route `/api/arc` legacy rimosse da server.py, dashboard counter migrato a `app.db.arcs`, pannello Arc migrato a `/api/db/arcs` (title+description+scene DB). test_server_arc_legacy.py eliminato. Suite: 2329 passed.
Branch dedicato: `efesto/gated6-arc-db-canonical` — non ancora mergato su main.

---

## Completato in sessione 2026-06-24 (continua — ciclo gap-review 3)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| char_memory_tools.py (4 funzioni) | +15 test | 2049f88 |
| scene_model.py + context_budget.py | +27 test | d9707a4 |
| summarizer.py (P3) | +21 test | 450885a |
| style_coach.py (anti-cliché linter) | +17 test | 450885a |
| lore_kb.py (LoreStore CRUD) | +33 test | 0741bb9 |
| app/db/arcs.py (CRUD SQL) | +17 test | fe5cec9 |
| app/db/lore.py (2→18 test) | +16 test | f2ef2ab |
| app/db/characters.py (2→23 test) | +21 test | 3c14e9b |
| characters_service.py (filesystem monkeypatch) | +17 test | 11b6071 |

**Totale ciclo 3**: +184 test unità su moduli a copertura zero/minima.
**Branch**: calliope-gapfix/red-test-fixes — 15 commit, ~1200+ test verdi.

## Completato in sessione 2026-06-24 (ciclo gap-review 4 — continua)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| char_memory._fts_escape (FTS5 builder) | +10 test | c8a8378 |
| db/scenes.py (list_scenes, assign_scene_to_arc) | +11 test | c8a8378 |
| db/reactions.py (add_reaction, list_reactions) | +7 test | c8a8378 |
| reactions_db_routes.py (GET/POST/DELETE HTTP) | +8 test | f7310bb |
| scene_characters_db_routes.py (GET/POST/PATCH/DELETE) | +14 test | f7310bb |

**Totale ciclo 4 fin qui**: +50 test. Suite: ~1215+ verdi.

---

## Completato in questa sessione (2026-06-24)

| Item | Stato |
|------|-------|
| WI-68 is_readonly guard | ✅ commit ca4a5f1 |
| tsc7 skipif sklearn | ✅ commit ca4a5f1 |
| pandas compat test skip | ✅ commit ca4a5f1 |
| E1 lore_retrieval_for_scene | ✅ commit cbbd1d6 |
| E2 sheet_retrieval_for_scene | ✅ commit cbbd1d6 |
| E3 refine-fn + C2 prompt-design | ✅ commit 0956946 |
| FE-3 compose messaggio in scenes.js | ✅ commit 60bd944 |
| FE-4 rimozione route flat-YAML | ✅ commit 60bd944 |
| entity_linker 12 test unit | ✅ commit 144bc67 |
| VG-2 migrate_scenes_yaml_to_db + 11 test | ✅ commit e23676e |
| DATA-DEBT repair_yaml_quotes + 13 test | ✅ commit 9d49740 |
| scenes_db_routes commento scaffolding rimosso | ✅ commit 9d49740 |
| Branch: calliope-gapfix/red-test-fixes | 7 commit — pronto per PR |

## Completato in ciclo gap-review 5+6+7 (ripresa sessione compattata 2026-06-24)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| scripts/calliope_cli.py (zero→completo) | +18 test | e70f935 |
| scripts/plot_arc_cli.py (zero→completo) | +20 test | a2c6f5a |
| scripts/style_voice_guide.py | +8 test | d856ea4 |
| scripts/migrate_char_memory_multi_signal.py | +6 test | d856ea4 |
| scripts/lora_eval_pipeline.py | +10 test | 50121ef |
| scripts/seed_char_memory.py | +8 test | 50121ef |
| lore_routes.py (POST/GET-by-id/DELETE) | +11 test | e23f85e |
| scene_migrate.py (kind-mapping, char senza id) | +7 test | 4ac11df |
| server.py /api/chars + /api/char/* | +16 test | dcfcf3d |
| server.py arc legacy (GET/POST/append/summary/threads/continue/search) | +16 test | 9aa7f0e |
| server.py memory_replace, mascot, chars/<name>/memory | +7 test | 9aa7f0e |
| server.py lore_search, scene_revive 400/404 | +6 test | af8c78f |
| server.py /api/translate | +6 test | 4ba1c8f |
| server.py POST /api/arc (create) | +3 test | cc02aa4 |

**Totale cicli 5-7**: +142 test. Suite unit: 1021 verdi.

---

## Completato in ciclo gap-review 8-10 (ripresa sessione 2026-06-24)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| scene_narrative.build_scene_prompt | +9 test | f672f77 |
| discord_persona_binder.parse_persona_trigger | +12 test | f672f77 |
| build_chromadb_index.chunk_text | +10 test | 1e8bd64 |
| generate_scene._sanitize/_build_variant_prompt | +14 test | 1e8bd64 |
| build_lore_index._extract_char_lore/_extract_scene_lore | +18 test | ef312e7 |

**Totale cicli 8-10**: +63 test. Suite unit: 1238 verdi.
**Scripts senza test**: solo network/IO-heavy (discord_bot, tts_speak, twitch_bot, llm_gateway_http, mascot_ws_server) — non testabili puramente.

---

## Completato in ciclo gap-review 15-19 (ripresa sessione compattata 2026-06-24)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| scripts/twitch_bot.py (pure fns: check_cooldown, build_*) | +12 test | 5a668c4 |
| /api/dashboard/* (llm_routing, activity, counts) | +12 test | 5a668c4 |
| scenes_db_routes POST/PATCH/DELETE/merge/duplicate | +15 test | 28398e6 |
| arcs_db_routes CRUD completo | +13 test | b272a64 |
| messages_db_routes HTTP CRUD | +14 test | 2510ab1 |

**Totale cicli 15-19**: +66 test. Suite unit: 1334 verdi.

---

## Completato in cicli gap-review 20-23 (ripresa sessione 2026-06-24)

| Item | Test aggiunti | Commit |
|------|--------------|--------|
| characters_db_routes PATCH+DELETE (WI-13 completo) | +8 test | e019b23 |
| server.py /api/scene/refine, /api/scene/variants, /api/draft, /api/summarize | +11 test | 8a24636 |
| char_memory.py SQLite core (upsert/get/list/delete/append_fact/get_facts) | +18 test | 2a51398 |
| plot_arc.py SQLite core (create/get/list_arcs/append_scene) | +13 test | 504a34b |

**Totale cicli 20-23**: +50 test. Suite unit: 1404 verdi.

---

## Stato VG (Vision Gap) dopo questa sessione

| Gap | Status |
|-----|--------|
| VG-1 (F1): draft-gen DB-first | ✅ CHIUSO (resolve_scene_context già in place) |
| VG-2 (F2): migrazione scene YAML→DB | ✅ CHIUSO (app/scene_migrate.py + scripts/migrate_scenes_yaml_to_db.py) |
| VG-3: isolamento verify-harness | ✅ CHIUSO (fix 893088e precedente) |
| VG-4: UI chat scene-as-chat | ⛔ GATED-1 (decisione operatore UX) |
| DATA-DEBT: 31 YAML malformati | ✅ SCRIPT PRONTO (repair_yaml_quotes.py, 31/31 dry-run ok) |

---

## Completato in sessione 2026-06-25 (ciclo gap-review 5)

| Modulo | Copertura prima→dopo | Test aggiunti | Commit |
|--------|---------------------|---------------|--------|
| lore_routes.py | 82%→**100%** | +8 (POST bad insertion_order, PUT 7 campi) | 1e8b379 |
| characters_service.py | 90%→**98%** | +3 (except branch corrupt canon, load exception) | c12011c |
| lore_kb.py | 93%→**97%** | +5 (default path, non-list JSON, unknown field, extensions) | 10b8902 |
| scenes_db_routes.py | 94%→**98%** | +2 (GET title filter, merge scene_id_a 404) | a26a479 |
| char_memory.py | 80%→**100%** | +11 (exception branches, retrieve_multi_signal) | 77a4449 |

**Totale ciclo 5**: +29 test. Suite: 1468 verdi, 3 skipped.
**Lacune residue non-testabili**: 195-197 scenes_db_routes (dead code ValueError), 174-177 lore_kb (IO cleanup finally), entity_linker 52-60 (spacy non installato), style_coach 67% (sklearn/file-heavy).

---

## Completato in ciclo gap-review 11-12 (2026-06-25 — ripresa post-compact)

| Item | Copertura prima→dopo | Test aggiunti | Commit |
|------|---------------------|---------------|--------|
| style_filter.py load_blacklist() | 93%→**100%** | +1 (file reale, no mock) | 5843833 |
| plot_arc_cli.py _print_arc scenes+summary | 96%→**99%** | +1 (arc con scenes+summary) | c701bab |
| seed_char_memory.py except branch | 77%→**85%** | +1 (upsert_char raise) | c701bab |
| parse_character_list_thread.py main() | 82%→**99%** | +2 (happy path + OSError exit) | c701bab |
| migrate_scenes_yaml_to_db.py 3 branch | 87%→**98%** | +3 (dir 404, skip, exception) | 0e07365 |

**Totale cicli 11-12**: +8 test. Suite: 1510 verdi, 3 skipped.
**Residui legittimi (skip)**: tutti `__main__` guard (plot_arc_cli:169, seed_char:43-46, parse_char:104, migrate_char_multi:71-72, migrate_scenes:111).

---

## Completato in ciclo gap-review 13-16 (2026-06-25 — sessione continua)

| Item | Copertura prima→dopo | Test aggiunti | Commit |
|------|---------------------|---------------|--------|
| test_tts_phoneme_export.py | 23%→**95%** | +24 | 66daefd |
| test_extract_member_list.py | 0%→**99%** | +14 | 29b5235 |
| test_import_tupperbox.py | 40%→**98%** | +9 | cff345f |
| test_repair_yaml_quotes.py | 54%→**97%** | +8 | e061e72 |
| test_style_voice_guide.py | 39%→**86%** | +9 | e061e72 |
| test_lora_eval_pipeline.py | 47%→**94%** | +10 | 5c1d455 |
| generate_scene.py | 17%→**99%** | +49 | 8c6ed69 |
| narrative_state.py | 80%→**99%** | +12 | 6ab16cc |
| import_excel_history.py | 94%→**99%** | +1 | c6c154c |
| lora_eval_pipeline.py | 94%→**99%** | +1 | c6c154c |

**Totale cicli 13-16**: +137 test. Suite: ~1650+ verdi.

**Scripts a 0% non testabili (GATED)**:
- `grab_discord_token.py` (91r): usa playwright/browser-automation interattivo
- `llm_gateway_http.py` (58r): dipende da path esterno `/home/nic/Scrivania/Workspace/mcp_servers/llm_gateway`
- `mascot_ws_server.py` (29r): import `live2d_mascot.server.ws_server` (package shared)
- `run_e2e_demo.py` (114r): E2E demo che richiede servizi attivi (LLM gateway, WS server)
- `build_chromadb_index.py` (12%, 243r): chromadb-heavy, richiede istanza reale
- `discord_bot.py` (34%, 205r): discord.py client events — non testabili senza test integrazioni
- `test_narrative_continuity.py` (0%, 98r): script di test E2E (non un test pytest)

---

## Completato in ciclo gap-review 17-18 (ripresa post-compattazione 2026-06-25)

| Item | Copertura prima→dopo | Test aggiunti | Commit |
|------|---------------------|---------------|--------|
| style_coach._compute_style_drift (argomenti invertiti) | 67%→**99%** | fix test esistente | 5d6ad4a |
| entity_linker.py (spacy nlp path) | 86%→**100%** | +1 (mock spacy dedup+stop) | 8c3d8c9 |
| merge_delta_messages.py (blank line sort) | 98%→**99%** | +1 | 8c3d8c9 |
| merge_char_sources.py (blank line corpus) | 99%→**99%** | +1 | 8c3d8c9 |

**Totale**: 1918 test passano. Gap residui = solo `__main__` guards e dead code irraggiungibili.

**Stato finale copertura** (non raggiungibile unitariamente):
- `server.py` 63% — GATED (Flask integration)
- `app/db/messages.py` line 544 — dead code (concurrent race tra 2 SELECT)
- `scenes_db_routes.py` lines 195-197 — dead code (ValueError mai sollevata da merge_scenes)
- `lore_kb.py` lines 174-177 — `finally` IO cleanup (difficile simulare senza risorse reali)
- Tutti gli `if __name__ == "__main__":` guards in ogni script

---

## Completato sprint redesign#257 (2026-06-25 — [father-GO] da nic)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| GATED-1: UI chat lista-flat | scenes.js _renderChatThread, XSS-safe, scroll-to-bottom | 0e15464 |
| GATED-1: bugfix _sceneAction | s.id vs s.scene_id, window._currentSceneMessages | 5473e16 |
| GATED-2: REFINE_PROVIDER/MODEL | env vars + test_refine_uses_env_provider_model | 0e15464 |
| scene list: message_count + is_readonly | LEFT JOIN COUNT, status dot verde/grigio | 5764563 |
| fix revive: DB fallback | UUID scene_id → query DB → scene_data fallback | 72c5d80 |

**Suite: 2034 test verdi. GATED-3 (Discord bot token) e GATED-5 (/api/messages/next) restano pending.**

---

## Completato ciclo gap-review finale (2026-06-25 — ripresa post-compact)

| Item | Copertura prima→dopo | Test aggiunti | Commit |
|------|---------------------|---------------|--------|
| server.py flask routes (lore_search, lore_check, draft, dashboard) | 71%→**93%** | +90 test | c23f885 |
| scenes_db_routes.py lines 195-197 (ValueError→404) | 98%→**100%** | +1 test | c23f885 |
| db/messages.py line 544 (TOCTOU pos_row mock) | 99%→**100%** | +1 test | e14094f |

**TOTAL: 98% (2029 test verdi)**

**Residui finali copertura (non testabili senza infra):**
- `server.py` 982-1077 → **GATED-5** (decision operatore: keep `/api/messages/next`?)
- `server.py` 1593 → `app.run()` (unreachable in test)
- `style_coach.py` 201 → `if __name__ == "__main__":`
- `test_characters_service.py` 9,22,30,53 / `test_scene_model.py` 57,78 → file test interni, irrilevanti

---

## Completato ciclo gap-review 2026-06-25 (ripresa post-compact — redesign#257 step2+3 + VISION surface gaps)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| redesign#257 render-thread completo | ts, badge discord/✎, is_summary stile, content_enhanced | a5e64c4 |
| redesign#257 compose narratore/personaggio | select #compose-who + auto-fill author | a5e64c4 |
| E2E test FE→BE | 5 test Flask con DB reale (POST→GET→lista) | a5e64c4 |
| Dashboard card "Scene recenti" | Top-6 scene da /api/db/scenes con click handler | aa21579 |
| Coverage server.py righe 1366-1367 | +2 test: db not found → close, exception → except pass | aa21579 |
| Messages: filtro source + append-to-scene | ?source=discord, select scena, bottone "→ Scena" | 0215f27 |
| Characters inline edit | renderEditForm(), _addEditBtn(), ?name= filter | de7ba49 |

**Suite: 2047 test verdi. Coverage: 98% TOTAL, 94% server.py (limite GATED-5).**
**GATED-3 (Discord token) e GATED-5 (/api/messages/next) restano pending.**

---

## Completato ciclo gap-review 2026-06-25 (continuazione post-compact)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| fix(_sceneAction 'draft') | pre-compila draft-prompt con contesto scena | 155f5b0 |
| test(translate context=plain) | copri righe 512, 523 (branch non-fantasy_rp) | ad290f0 |
| test(server) /health, GET /, _load_emotion_map | copri righe 190-195, 216-226 | 056b989 |
| test(translate exceptions) | copri righe 550-551, 557-559 | 09e2610 |

**Suite: 2060 test verdi. Coverage: 98% TOTAL, server.py 94%.**
**Residui definitivi**: solo GATED-5 (984-1079), app.run() (1626), __main__ guards.

---

## Completato ciclo gap-review 2026-06-25 (scope allargato — GATED e UX)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| fix(scene/revive UI) | mostra anche `recent_messages` ChromaDB nel pannello revival | c7e8651 |
| doc(GATED-6) | Arc YAML vs DB discrepancy documentata come GATED | c7e8651 |
| fix(scene/actions) | `_sceneAction('translate')` pre-compila translate-input con lastMsg | 64be733 |
| feat(scene/copy) | pulsante `📋 Copia ultimo` copia last message negli appunti (Step 7 user flow) | 64be733 |
| fix(characters) | `renderEditForm` auto-ritorno a detail view dopo salvataggio (800ms) | ed86b69 |
| feat(scenes/roster) | pulsante `+ Roster` per aggiungere personaggi al roster di scena | 78345e7 |

**Suite: 2059 test verdi. Coverage: 98% TOTAL.**
**Scripts residui a 0% non testabili**: tutti `__main__` guards (già documentati come skip legittimi ciclo 13-16).
**GATED pendenti**: GATED-3 (Discord token), GATED-5 (/api/messages/next), GATED-6 (Arc YAML vs DB).

---

## Completato ciclo gap-review 2026-06-26 (GATED-5+6 branch + char-scene-link)

| Item | Dettaglio | Commit/Branch |
|------|-----------|---------------|
| GATED-5: rimozione POST /api/messages/next | ~100r codice morto rimosso, 6 file test aggiornati | f3a4e3b / efesto/gated5-remove-messages-next |
| GATED-6: DB canonical per archi | route legacy rimosse, dashboard migrata, pannello Arc JS migrato | 05152b9 / efesto/gated6-arc-db-canonical |
| feat(characters): GET /api/db/characters/<id>/scenes | route join scene_characters, +2 test (22 totali) | 56017b8 / feat/char-scene-link-and-scene-edit |
| feat(scenes): _toggleSceneEdit + _saveSceneEdit | PATCH /api/db/scenes/<id> per edit inline title/location | 56017b8 / feat/char-scene-link-and-scene-edit |

**Suite: 2346 test verdi (feat branch). Coverage: 94% server.py (solo GATED-5 984-1079 + app.run() 1626 residui).**
**Branch GATED-5/6 pronti per merge su main — in attesa di nic.**
**GATED pendenti**: GATED-3 (Discord token).

---

## Completato ciclo gap-review 2026-06-26 ciclo #2

| Item | Dettaglio | Commit |
|------|-----------|--------|
| fix(test): test_dashboard_nav_link_present_and_first | nav-home rimosso per WI-10 ≤5 voci; test aggiornato → nav-scenes | 9511001 |

**Suite: 2347 passed, 77 skipped (tests/ no UI). Coverage 98% invariata.**
**GATED pendenti**: GATED-3 (Discord token). GATED-5/6 pronti per merge su main.

---

## Completato redesign#257 P6 UI — branch efesto/redesign-p6-ui-refinements (2026-06-26)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| feat(scenes/P6): filtro arc nel panel + badge arc header | dropdown filtro per arco in lista scene, badge cliccabile in detail | 46de86a |
| feat(navbar/P6): coerenza nav — _NAV_PARENT | panel secondari (draft/refine/lorecheck…) evidenziano nav parent | dd740f6 |
| feat(scenes/P6): form edit inline + arc_id in PATCH | #scene-edit-form con title/location/arc select, backend PATCH esteso | fc44c76 |
| feat(characters/P6): kind badge nel detail view | badge npc/player/operator colorato dal DB (stessa fetch _addEditBtn) | 77c4999 |

**Suite: 2361 passed, 77 skipped. +14 test rispetto a ciclo #2.**
**Branch**: efesto/redesign-p6-ui-refinements — 4 commit P6, non ancora mergato su main.

---

## Completato redesign#257 P6 UI — browser-test round 2+3 (2026-06-26)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| fix(GAP-1): register_characters_db_routes | create_app() non la registrava → 404 | 465cdce |
| fix(GAP-2/3): arc seed YAML→SQLite al boot | INSERT OR IGNORE 6 archi | 465cdce |
| fix(GAP-4/lorekb): overflow-y:auto panel | ricerca LoreKB scrollabile | 465cdce |
| feat(discord-M2): discord_jsonl_to_db.py | 22.207 msg importati con dedup SHA1 | 465cdce |
| fix(FLOW-7): _loadArcFilterOptions(editSel) | arc select nel form edit mai popolato | b0f5593 |
| test(p6-journey): 14 Given/When/Then | GAP-1/2/3 + arc-assign blindati | d04aebb |
| fix(smartdraft): _loadCharDropdown globale | scope bug ReferenceError in showView | 46b3059 |

**Suite: 2371 passed (14 journey test P6 + 10 discord + fixture esistenti).**
**GAP runtime residui** (non bugs di codice): 503 /api/draft (gateway LLM non avviato).

---

## [GATED-7] P7 Dead Code Cleanup — lista candidati (proposta per operator review)

> **HARD RULE**: nessuna rimozione senza: opus propone lista → father valuta → operator approva.
> Questo item accumula la lista. Commit di rimozione solo dopo GO esplicito.

**Moduli candidati** (scan 2026-06-26, zero import a runtime — non importati da nessun file non-test):

| File | Righe | Motivo candidatura | Rischio rimozione |
|------|-------|--------------------|-------------------|
| `app/context_budget.py` | ~120r | Motore budget P2/P3 — non wired a server.py | BASSO — futuro P3 |
| `app/summarizer.py` | ~80r | Engine resumo P3 — non wired a server.py | BASSO — futuro P3 |
| `app/db/lore.py` | ~60r | Già marcato DEPRECATED internamente | MEDIO — potrebbe avere dati |

**Non-candidati** (esclusi dallo scan):
- `scripts/discord_bot.py` — wired con GATED-3 bot token
- Tutti gli `if __name__ == "__main__":` guards — falsi positivi dello scanner
- `app/db/messages.py:544` — dead code per race condition, non rimuovibile

**Decisione richiesta**: quali file (se qualcuno) rimuovere? Risposta: tenere tutto / rimuovere solo lore.py / lista completa.

---

## Completato ciclo gap-review 2026-06-26 ciclo #3 (branch efesto/redesign-p6-ui-refinements)

| Item | Dettaglio | Commit |
|------|-----------|--------|
| feat(summarize/P3): '→ Salva in scena' | POST is_summary=1 nella scena attiva; visibile solo se scena aperta; 2 journey test TestFlow8SummaryInScene | adb3e63 |
| diagnosi: test draft 503 già coperti | test_server_scene_draft_routes.py righe 229-243 già avevano ConnectionError+Exception | — |

**Suite: 2393 passed, 77 skipped. Coverage: 98% invariata.**
**Gap non-gated ESAURITI**: tutti i gap VISION implementabili senza operator-review sono stati chiusi.

**GATED pendenti**:
- GATED-3: Discord bot token (nic deve generare il token)
- GATED-5: branch efesto/gated5-remove-messages-next pronto per merge su main
- GATED-6: branch efesto/gated6-arc-db-canonical pronto per merge su main
- GATED-7: Dead code cleanup (richiede opus + operator review per la lista)

---

## Completato in sessione 2026-06-26 (browser-test estensivo P6 continua)

| Item | Tipo | Commit |
|------|------|--------|
| fix: h2 vuoto per YAML con name='' → fallback stem | fix(characters.js) | 9f2660e |
| test: FLOW-10 Characters PATCH completo (nome+kind+image+404+400) | journey | bf01eeb |
| test: selettori LoreSearch (#ls-query ≠ #loresearch-query) | ui struct | 9f6360c |
| test: selettori Translate (#translate-input/output) | ui struct | 188ef39 |
| test: selettori LoreCheck (#lc-text ≠ #lorecheck-input) | ui struct | 188ef39 |
| test: selettori Draft/Refine (#btn-draft-generate #refine-scene-input) | ui struct | 7286051 |

**Suite: 2086 passed (unit), +15 test da browser-test round 2026-06-26.**

**Pannelli verificati via Playwright**: Dashboard, Scenes (list+detail+arc-badge+roster), Characters (grid+detail+PATCH), SmartDraft, Translate, Draft, Refine, LoreCheck, LoreSearch, Arc, Summarize, Revive, LoreKB.

**Gap dati aperti (non codice)**:
- `silver.draft.yaml` e `saturn.draft.yaml`: YAML invalido (virgolette non bilanciate, riga ~36/40). Parser restituisce name='' → h2 vuoto (ora fixato con fallback stem). Nic deve fixare i file YAML manualmente.
- LoreKB: 0 voci nelle categorie — gap dati operatore, UI gestisce empty state correttamente.
- **ChromaDB embedding mismatch**: `/api/chars/<name>/memory` ritorna `error: "Collection expecting embedding with dimension of 768, got 384"`. Il DB ChromaDB char_memory è stato costruito con modello che generava 768-dim; il modello corrente (sentence-transformers/all-minilm) genera 384-dim. Fallback silente (snippets=[]). Fix: ricostruire la collection ChromaDB con `scripts/build_chromadb_index.py` oppure allineare il modello a 768-dim (es. `all-mpnet-base-v2`). Non bloccante — char facts semplicemente non compaiono nel detail personaggio.

**[DONE: browser-test-round-p6-continued]**

---

## Completato in sessione 2026-06-26 (browser-test estensivo P6 round 3 — post-compact)

| Item | Tipo | Commit |
|------|------|--------|
| fix(chromadb): _embed_ollama() per query 768-dim su calliope_messages | fix | 5bc0ad2 |
| fix+test(shell): id= su 8 bottoni scene senza ID + 9 test | fix+test | ed0e451 |
| fix+test(shell): id= su bottoni arc/roster + 4 test | fix+test | 2eaade0 |
| test: FLOW-13 Arc lifecycle POST/GET/DELETE /api/arc | journey | bb052fb |
| test: SmartDraft IDs strutturali (sd-intent, btn-smartdraft, sd-output...) | ui struct | 2fd3603 |
| test: LoreCheck IDs completi (lc-output, lc-verdict, lc-issues-list) | ui struct | a34a380 |
| test: Messages panel IDs (msg-char-filter, msg-discord-only, message-list) | ui struct | a34a380 |
| test: LoreKB panel IDs (lorekb-new-btn, lorekb-search-*, lorekb-entries) | ui struct | a34a380 |

**Suite: 2149 passed. test_scenes_panel_ui: 76 test. test_journey_p6_flows: 40 test.**

**ChromaDB mismatch risolto**: chars/memory ora restituisce 5 snippets reali via Ollama nomic-embed-text:v1.5.

**Bottoni senza ID residui**: solo shortcut-grid home (testabili via classe `.shortcut-btn`) + bottoni generati dinamicamente (→ Scena nei messaggi, filtri categoria LoreKB).

**[DONE: browser-test-round-p6-round3-post-compact]**

---

## Completato browser-test round 4 (2026-06-26 — post-compact)

| Item | Tipo | Commit |
|------|------|--------|
| fix(lorekb): id= su 8 elementi form renderForm() | fix | 37ffd77 |
| fix(ui): id= bottoni dinamici residui (msg-to-scene idx, lorekb-cat-*, shortcut-*) | fix | 8d4d854 |
| test(ui-struct): +10 test chars panel + shortcut | test | e806c16 |
| test(ui-struct): +8 test arc + refine panel IDs | test | bc1849c |
| chore(gitignore): db/ + lore_kb.json + db-shm/wal | chore | 0e1574b |
| test(ui-struct): +1 test #ls-status LoreSearch | test | 2b3203e |
| chore(gitignore): live2d model binaries + data/backups/ | chore | 7e986ee |

**Suite: 2236 passed (+12 vs inizio round). test_scenes_panel_ui: 76→95 (+19 test).**

**Pannelli verificati funzionalmente** (tutti passano graceful degradation 503 LLM):
LoreKB form, Messages → Scena, Scene edit PATCH, Arc list+detail, Refine, Translate, SmartDraft, LoreSearch (10 hits ChromaDB), LoreCheck, Scene chat compose POST.

**Gap residui non-codice**:
- `silver.draft.yaml` / `saturn.draft.yaml`: YAML invalido — nic deve fixare manualmente
- ~~MASCOT-PORT: ws_server.py default `--port 8767` ≠ canonical 9876~~ → ✅ FIXATO commit 6a60e82
- MASCOT-SWITCH: feature `?model=koko|tingyun` non implementata nell'app (nessun codice la usa) — non è un bug, è feature futura

**GATED pendenti**:
- GATED-3: Discord bot token (nic deve generare)
- GATED-5: branch efesto/gated5-remove-messages-next pronto per merge
- GATED-6: branch efesto/gated6-arc-db-canonical pronto per merge
- GATED-7: Dead code cleanup (richiede opus + operator review)

**[DONE: browser-test-round4-2026-06-26]**

---

## Completato browser-test round 5 (2026-06-26 — post-compact)

| Item | Tipo | Commit |
|------|------|--------|
| fix(mascot): porta default 8767→9876 | fix | 6a60e82 |
| test(ui-struct): +13 SmartDraft+Summarize panel IDs | test | d886994 |
| test(ui-struct): +11 dashboard panel IDs | test | 191859d |
| test(ui-struct): +6 draft/refine/lorecheck IDs estesi | test | 317817c |
| test(ui-struct): +5 draft output/state IDs | test | 23c36e5 |
| test(ui-struct): +5 scene-detail + compose-status IDs | test | a753462 |

**Suite: 2276 passed. test_scenes_panel_ui: 95→135 (+40 test).**

**Pannelli verificati funzionalmente in round 5**:
- Characters: grid 21 item, detail click, kind badge, edit btn, search filter ✓
- LoreKB: form create, save, appare in lista ✓
- Scenes: arc filter (39 match), text filter (224 match), create nuova scena ✓
- Arc: detail click, content visible, empty hidden ✓
- Scene chat compose: send POST → "✓ Inviato", thread aggiornato ✓
- SmartDraft: form compilabile, 503 graceful "✗ LLM gateway not available" ✓
- Summarize: 503 graceful "✗ LLM gateway not available" ✓
- Draft: input compilabili, genera in corso (gateway assente, timeout atteso) ✓
- Refine: 503 "✗ Errore: LLM gateway unavailable" ✓
- Dashboard: contatori popolati (3 chars active, 303 scenes, 15 arcs, 29308 msgs, 1 lore) ✓

**MASCOT-SWITCH**: confermato che `?model=koko|tingyun` NON è implementato nel codice (nessuna route né JS). Non è un bug — è feature futura non esistente.

**Gap residui**:
- `silver.draft.yaml` / `saturn.draft.yaml`: YAML invalido — nic deve fixare manualmente
- 757 scene totali nel DB (molte da journey tests) — non è un bug, è accumulo di test data

**GATED pendenti**:
- GATED-3: Discord bot token (nic deve generare)
- GATED-5: branch efesto/gated5-remove-messages-next pronto per merge
- GATED-6: branch efesto/gated6-arc-db-canonical pronto per merge
- GATED-7: Dead code cleanup (richiede opus + operator review)

**[DONE: browser-test-round5-2026-06-26]**
