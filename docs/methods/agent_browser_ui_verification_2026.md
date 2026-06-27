# Agent Browser-UI Verification (2026) — verifica a STATO-RISULTANTE, non a presenza

> Metodo per agenti che verificano/riparano web-UI. Nato dal lavoro scene-chat Calliope
> (giugno 2026). Skill che lo opera: `ui-vision-gap-review` (~/.claude/skills/).

## Tesi
Un agente scopre i bug di una UI **usandola come un utente vero**, e li blinda asserendo lo
**STATO RISULTANTE** dell'azione — non la presenza degli elementi. La presenza inganna: a Calliope
un turno persisteva ma finiva in posizione sbagliata; un verify "il messaggio è nel thread" passava,
il bug restava.

## Principi
1. **Stato-risultante, non presenza.** Dopo l'azione, asserisci il DOM risultante (es. il turno è
   l'ULTIMA bolla, è attribuito al personaggio giusto) E la **persistenza dopo reload**.
2. **Given-When-Then scritti PRIMA.** Es.: "Given scena-attiva, When invio-messaggio, Then il turno
   compare come ultima bolla col suo testo E persiste dopo reload."
3. **Selettori user-facing + auto-retry.** Preferisci ruolo/label/testo a CSS-fragili; usa
   `expect()`/`wait_for_function`, MAI `sleep` fisso.
4. **Adversarial.** Inietta errori realistici (503/queue-exceeded, rate-limit, input-ambiguo): l'utente
   deve vedere spinner+messaggio-chiaro+retry, MAI un DOM rotto. Distingui retry-able (503/throughput)
   da definitivi (400/401/quota): no-retry sui definitivi.
5. **Isola lo stato.** Env-override del DB/filesystem (`*_DB_PATH`, `*_CHARS_DIR`) + DB temp + stub dei
   servizi esterni → i journey sono committabili, ripetibili, senza inquinare i dati reali.
6. **Live-explore poi cristallizza.** Per SCOPRIRE i gap, pilota dal vivo (Playwright-MCP se presente,
   altrimenti Playwright-Python esplorativo che dumpa stato/affordance/404/console-errors). Per la
   REGRESSIONE, cristallizza il flusso in un journey GWT committato, rilanciato a inizio-sessione.

## Trappole catturate
- Verify-di-presenza (vedi sopra).
- A-tavolino: dedurre dal codice che "si può fare" mentre dal vivo il select è vuoto / la route non è
  registrata in `create_app` / due sottosistemi non sono wired (a Calliope: roster vuoto su tutte le
  scene + `/api/db/characters` non registrata → "scrivere come personaggio" era impossibile).
- Fix-architetturale unilaterale: i gap su modello-dati/unificazioni si **flaggano all'operatore**,
  non si risolvono di testa propria (gate-redesign).

## Esempio applicato (Calliope scene-chat)
Gap trovati USANDO l'app, non leggendo il codice: message-render (position_order da import
non-contiguo → append `MAX+1`), refine-503 (retry+failover+breaker+msg-pulito), home-vuota (iframe
SillyTavern spento → landing riprogettata), authoring-come-personaggio impossibile (roster vuoto +
route non-registrata + nessuna affordance binding). Regressione: `scripts/journey_scene_chat.py`
(8 journey GWT). Vedi memoria `project-scene-chat-usability`.
