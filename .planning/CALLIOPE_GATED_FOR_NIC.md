# Calliope — Decisioni GATED per operatore (nic)

> Aggiornato: 2026-06-24 (ciclo 8-10) da sonnet-orch-calliope.
> File accumulativo: ogni sessione appende le decisioni bloccanti. Rimuovi la riga dopo che hai dato il via libera.

---

## [GATED-1] UI chat JanitorAI — C1 (design + layout)

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

## [GATED-2] Config gateway-strong-uncensored — C3

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

## [GATED-4] Redesign JanitorAI P0-P6 strutturale

**Blocco**: VISION menziona "restructure JanitorAI P0-P6". La spec `CALLIOPE_REDESIGN_SPEC.md` è in `.planning/`. Toca:
- paradigma scene=chat (backend DONE, frontend mancante → vedi GATED-1)
- widget/overlay audio-visivi (Live2D mascot DONE, TTS attivo)
- future abliteration locale (OBLITERATUS)

**Gate**: non strutturare finché operatore non ha confermato approccio su GATED-1.

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
