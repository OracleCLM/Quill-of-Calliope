---
title: "Calliope — VISION Rewrite (P0 foundation, scene-centric)"
type: vision-rewrite
status: draft-p0
created: 2026-06-03
operator-mandate-ref: "2026-06-03 01:29 GO MASSIMA INDIPENDENZA"
supersedes: "VISION.md (milestone-style M0-M6)"
---

# Calliope — VISION Rewrite (P0, scene-centric)

> Musa della poesia epica. Sistema locale single-user per scrittura RP e gestione sessioni di gioco di ruolo testuale multi-personaggio.

---

## Long-term goal (anno+)

Calliope è un sistema locale single-user per la scrittura di role-playing e la gestione di sessioni di gioco di ruolo testuale multi-personaggio. Core: formato chat multi-personaggio (Scene), knowledge base lore editabile operator-curata, AI-assisted draft con operator-in-the-loop mandatory, output verso Discord (scraping inbound futuro, outbound parked).

---

## Principi fondamentali

### 1. Scene = chat multi-personaggio
Una Scene è una chat con history messaggi condivisa + member list di personaggi. Multi-personaggio (vs Janitor: 1-user-1-bot è il limite che Calliope supera). Più scene in parallelo, raggruppate per Arc, ordinate per data o nome. Formato chat = chronological message log parsabile. Nessuna cerimonia speciale di apertura/chiusura.

### 2. Lore = KB editabile 5 categorie
La sezione Lore diventa una knowledge base sfogliabile e modificabile, impaginata per argomento. 5 categorie confermate:
1. World/Setting
2. Places — capitali & città
3. Characters & Events
4. Mechanics/Magic Lore
5. Other

Contenuto operator-supplied (NO extraction automatica o analisi dataset). L'operatore popola e cura le voci manualmente. Ricerca semantica resta come secondo passo opzionale (canonical entries first, poi vector search).

### 3. Summarize integrato in scene
Nessuna sezione Summarize separata. L'operatore seleziona un range di messaggi → auto-summarize → nota memory editabile (is_summary=TRUE nel DB). Stesso motore comprime messaggi vecchi per budget context window prima di ogni chiamata AI.

### 4. Smart-draft response-prefill (Janitor-style)
Operator scrive primo draft (IT o EN) + campo istruzioni direttive separato (stile/tono/goal — NON testo da tradurre, ma direttive). AI genera singola uscita enhanced/tradotta. NO swipe multipli — rigenerare con nuove istruzioni o editare manualmente. Operator sempre in the loop.

### 5. 5 superfici — collasso da 13 tab
Tutto il dashboard collassa in 5 superfici:
- **Scenes** (core)
- **Characters** (sostituisce Home — schede char editabili, immagini)
- **Lore** (KB vera, 5 categorie)
- **Messages** (views dual + scraping Discord trigger)
- **Dashboard** (landing thin — scene recenti + messaggi scraped recenti)

Tutto il resto (Summarize/Draft/Refine/Translate/Arc-tab) confluisce DENTRO le Scenes.

---

## Roadmap P0→P7

| Fase | Scope |
|------|-------|
| **P0** | Spec consolidation — VISION rewrite + DB schema + user flow (questo sprint) |
| **P1** | Scene core — chat format, member list, message CRUD |
| **P2** | Smart draft — campo istruzioni + enhance/translate integrato in scena |
| **P3** | Lore KB — 5 categorie, add/edit/create voci, ricerca semantica second-step |
| **P4** | Characters — schede V2/V3 spec, immagini, edit diretto |
| **P5** | Messages — views dual (all + last-scrape), scraping incrementale Discord |
| **P6** | Efesto integration — free models only, auto-rotate, avviso chiavi scadute |
| **P7** | Cleanup — dead code, old spec archive (gated: opus + operator review) |

---

## Non-goals

- NO sceneggiatura cinematografica linear-script
- NO full automation senza operator review (human-in-the-loop mandatory)
- NO LLM unfettered (sempre operator-gated)
- NO multi-user / multi-tenant (single operator NM)
- NO modelli a pagamento (operator-mandate)
- NO Discord bot outbound (parked — codice M6 già pronto, attivazione pending totale)
- NO swipe multipli (rigenerare con nuove istruzioni invece)

---

## Efesto integration note

Quando Efesto è ready: offload AI calls a Efesto CLI per cost saving (free models groq/cerebras/openrouter); Claude API come fallback raro e selettivo. Auto-rotate su model-not-found (rileva errore `model-not-found` + chiave valida → sceglie modello vivo stesso provider → aggiorna config autonomamente). Avviso all'avvio se tutte le chiavi falliscono X giorni consecutivi.

---

## Mascot (parked, retained)

Infrastruttura Live2D già presente (`frontend/live2d/`, `mascot_ws_server.py`, `static/js/mascot.js`). Parked come fase futura esplicita — NON eliminare dalla VISION. Quando attivata: dentro Scene con animazioni state-driven (reasoning/writing/TTS-reading). Progettare come asset condivisibile con Vesta (prevista interfaccia 2D).
