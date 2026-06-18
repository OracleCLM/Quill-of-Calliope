---
title: Calliope — Redesign JanitorAI-style — PROPOSTA CONVERGENTE (orch→nic)
date: 2026-06-18
status: PROPOSAL — operator-gated (HALT, attende convergenza nic)
base_research: ~/Documenti/ObsidianVault/060_PROJECTS/Calliope/2026-06-18_calliope_janitorai_redesign_research.md
owner: orch-calliope-opus
tags: [calliope, redesign, character-card, lorebook, discord-import, proposal]
---

# Calliope Redesign — Proposta convergente per nic

> Questa proposta NON rinegozia le decisioni LOCKED in VISION (2026-06-16). Le rende
> implementabili. Si appoggia interamente alla ricerca evidence-based (Character Card V2/V3,
> JanitorAI, SillyTavern World-Info) + ispezione del codice reale. **Nessuna implementazione
> parte finché nic non converge sui 3 decision-gate (§DECISIONI).**

## Diagnosi-radice unica
Tutti i 5 fronti del redesign collassano su **un solo difetto strutturale: store multipli non
sincronizzati**.
- Personaggi vivono in **3 store** disallineati: filesystem YAML (`characters/*.yaml`), tabella DB
  `characters.card_json` (quella legata alle scene via `scene_characters`), tabella legacy
  `character_sheets` (usata solo dal refine). → da qui la **discordanza** "personaggi pieni nelle
  chat ma vuoti in Lore>Personaggi": la chat legge il DB `characters`, la vista Lore enumera i YAML
  / la categoria lore-KB. Due viste, store diversi.
- Lore: `characters_events` mescola PERSONAGGI ed EVENTI; persistenza duale `data/lore_kb.json` ⟂
  tabella SQL `lore_entries`.
- Tool-scrittura: 6+ route divergenti (draft/translate/refine/continue/summarize/lore-check) che
  fanno la stessa cosa concettuale (trasformazione testo guidata-da-contesto) con assemblatori di
  prompt diversi.

**Tesi della proposta: una single-source-of-truth (`characters.card_json` = Character Card V2/V3) +
un assemblatore-prompt condiviso risolvono (a),(b),(c),(e) insieme.**

## Le 5 risposte (sintesi — dettaglio in ricerca §4)

**(a) Sezione PERSONAGGI dedicata** — schede ricche stile JanitorAI/Card-V2 che alimentano la
generazione, separate da Lore/Eventi.
- SSOT = `characters.card_json` schema **Character Card V2** (`{spec, spec_version, data{...}}`),
  con campi-prompt (`description, personality, scenario, first_mes, mes_example, system_prompt,
  post_history_instructions`) distinti dai cosmetici (`creator_notes, tags`).
- `extensions.calliope` per i nostri campi: `speech_pattern, backstory, kind(operator|player|npc),
  discord_aliases, image_path, char_memory_ref` (migrati dai YAML).
- **VINCOLO nic (2026-06-18): migrazione ADDITIVA/NON-distruttiva — si TENGONO tutti i personaggi.**
  `characters/*.yaml` e `character_sheets` **NON vengono rimossi né cancellati**: restano intatti
  come fonte di import/export e backup. Il DB `characters.card_json` diventa la SSOT *di lettura*
  per UI+generazione, popolato da un merge che PRESERVA ogni char esistente (nessuna perdita).
  Eventuale deprecazione fisica = decisione futura separata, gated come il cleanup.

**(b) Lore semplificata** — split netto in due viste:
- **PERSONAGGI**: vista sullo STESSO store `characters` DB (i char attivi in scena = sempre
  iniettati, "constant" impliciti). → la discordanza sparisce by-design.
- **EVENTI / WORLD-INFO**: `LoreEntry` key-triggered (`world_setting, places, mechanics_magic,
  events, other`). Allineare `triggered_entries()` allo standard: **whole-word match** (oggi
  substring → falsi positivi), opz. secondary-keys + token-budget. `scope=character` → mappa su
  `character_book` embedded della scheda. Unificare persistenza su DB `lore_entries`.

**(c) Interfaccia UNIFICATA tool-di-scrittura** — un "pannello azioni contestuale":
- UI: menu-azioni unico nel composer/su testo-selezionato — *Genera·Continua·Rifinisci·Traduci·
  Riassumi·Coerenza-lore*; una text-area intent + dropdown char-focus; output in diff/preview
  Accetta/Scarta (→ `content_enhanced`).
- Backend: collassare in **`POST /api/write {action, scene_id, text|intent_it, char_focus, ...}`**
  con **un assemblatore-prompt condiviso** (oggi divergono); route legacy come thin-wrapper per
  back-compat/test. Qui vivono in un solo posto: budget-cap, retrieval (schede-attive + lore
  key-match + char_memory), style_coach auto-lint, scelta-gateway.

**(d) Scraping Discord — span-temporale + canali**:
- `since`/`until` (ISO) in `/preview`+`/to-scene`, filtro sul `timestamp` già parsato (date-picker).
- `/scan` ritorna lista canali con metadati (name, category, count, date-range) → **multi-select**.
- (gated da decisione #3) import **live** = wrap DiscordChatExporter `--channel --after --before`.

**(e) Discordanza personaggi** — spiegata: chat legge `characters` DB (via `scene_characters`),
Lore>Personaggi enumera YAML/lore-KB; store non sincronizzati. Fix = (a)+(b): fonte unica DB,
sezione PERSONAGGI che legge quella stessa fonte.

## Roadmap implementabile (POST-convergenza — sequenza phase-gated)
Ordine pensato per Efesto(meccanico single-file) + sonnet/opus(UI/retrieval/migrazione):
1. **M-A DATA** — migrazione **ADDITIVA** `character_sheets`+YAML → `characters.card_json` V2
   (merge che PRESERVA tutti i char, sorgenti originali INTATTE); loader/saver SSOT; YAML
   import/export wrapper. (mix: migrazione=opus, schema-edit=efesto). *Gate: backup pre-migrazione +
   verifica conteggio char pre/post == (nessuna perdita).*
2. **M-B PROMPT** — assemblatore-prompt condiviso + budget-cap; `POST /api/write` dispatcher; legacy
   route → wrapper. (opus/sonnet — instruction-heavy).
3. **M-C LORE** — split UI Personaggi/Eventi; whole-word match + token-budget; persistenza unica
   `lore_entries`. (sonnet UI + efesto per match-fn).
4. **M-D UI WRITE-PANEL** — pannello azioni contestuale nel composer (sonnet/opus).
5. **M-E DISCORD** — span-temporale + multi-canale (efesto additivo); live-wrap solo se decisione #3=sì.
Ogni milestone: ruff=0 + test mirati + browser-verify reale; commit main.

## DECISIONI che spettano a nic (HALT — convergere PRIMA di M-A)
1. **SSOT personaggi (riformulata post-vincolo nic)**: confermi di fare di `characters.card_json`
   (DB, Card V2/V3) la fonte-unica di **lettura** per UI+generazione, con migrazione **additiva** che
   TIENE tutti i char e lascia INTATTI YAML + `character_sheets` (nessuna deprecazione/cancellazione
   ora)? — questo basta a risolvere la discordanza senza toccare i dati esistenti.
2. **Budget permanent-token**: imporre un **cap** (~2-2.5k token stile JanitorAI, con troncamento
   schede/lore) per evitare degrado-memoria, OPPURE il gateway cloud-strong ha context ampio a
   sufficienza e preferisci **"tutto-dentro"**?
3. **Import Discord**: aggiungo l'import **LIVE** (wrap DiscordChatExporter `--after/--before/--channel`)
   oppure basta **arricchire il flusso da-file** esistente con span-temporale + multi-canale?

Secondarie (default proposti, modificabili): match lore whole-word con toggle per-entry;
`post_history_instructions` come leva uncensored/stile (default globale configurabile + override
per-scheda).
