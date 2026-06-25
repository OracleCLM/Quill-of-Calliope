# Calliope — Decisioni GATED per operatore (nic)

> Aggiornato: 2026-06-25 (ciclo gap-review ripreso, coverage 98%) da sonnet-orch-calliope.
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

## [GATED-5] POST /api/messages/next — mantenere o rimuovere?

**Blocco**: La route LLM-gen "genera prossimo messaggio" (riga ~1044 server.py) usa char_memory + ChromaDB + gateway per generare il prossimo turno in stile LLM. FE-4 ha rimosso le route CRUD flat-YAML ma non questa (è una feature, non solo CRUD).

**Domanda**:
- (a) Rimuovere del tutto (nuovo paradigma = write/edit manuale via FE-3)?
- (b) Mantenerla e collegare il bottone "Genera prossimo msg" esistente in shell.html al nuovo scena DB (scene_id dal DB invece che da flat-YAML)?

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
