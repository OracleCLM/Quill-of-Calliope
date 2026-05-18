<!-- Calliope.AI scene running summary template -->
<!-- Copia in scenes/<scene_id>.md per ogni scena attiva. -->
<!-- IMPORTANTE: scene long-tail (settimane/mesi tipici). Persistence forever-by-default. -->

---
scene_id: scene_XXX_descriptive_name  # es: scene_005_river_crossing
title: Brief title human-readable
location: <location_description>
date_started: 2026-MM-DD
last_active: 2026-MM-DD
status: active  # active | dormant | concluded | archived
mood: <one-word>  # tense | peaceful | mysterious | romantic | violent | comedic | etc
participants:  # list char_id
  - kazuki_takeda  # operator pc
  - emiko_yamashiro  # other_player_alice
  - npc_merchant_old  # npc
discord_channel: <channel_name>  # se rilevante
related_scenes:
  - scene_001_yamato_temple  # past lead-in
  - scene_006_<future>  # future continuation potenziale
related_lore:
  - "[[creature_kitsune]]"
  - "[[geography_yamato_valley]]"
duration_real: 3w 2d  # auto-calc da date_started a last_active
turn_count: 47  # numero exchanges totale
---

# <Scene Title>

## Running summary

Riassunto narrativo della scena dall'inizio. Aggiornato dopo ogni session significativa.

Mantenere conciso (200-500 parole). Per dettagli granular vedere `recent_exchanges` sotto.

Esempio:
> Kazuki ed Emiko hanno deciso di attraversare il fiume Tsubasa all'alba per evitare i bandit pattuglie. Sulla riva incontrano un vecchio mercante che offre informazioni in cambio di un favore...

## Recent exchanges (ultimi 5-10 messaggi)

Copia gli ultimi messaggi rilevanti dalla scena Discord, per context immediato draft generation.

> [2026-05-12 22:15] **Emiko**: She looked up at him, eyes catching the first light. "Do you trust him?"
> 
> [2026-05-12 22:30] **Kazuki**: *His hand rested on the hilt, but did not draw.* "Trust is a luxury we cannot afford."
> 
> [2026-05-13 09:00] **Merchant**: "Trust me or not, the answer you seek lies across the river. But the path... it has a price."

## Pending threads

Cose che devono essere risolte/affrontate nei prossimi turni:

- [ ] Kazuki deve rispondere alla domanda del mercante sull'artefatto
- [ ] Emiko ha appena svelato un segreto del suo passato, Kazuki non ha ancora reagito
- [ ] Il fiume sta crescendo per la pioggia notturna, time pressure crescente

## Operator notes

Spunti per future development, cose da ricordare:

- "Aurora dovrebbe entrare in scena entro 3-4 turni se mantengo timeline"
- "Il mercante può rivelarsi alleato kitsune sotto travestimento (lore [[creature_kitsune]])"
- "Evitare di mostrare l'artefatto in dettaglio prima di scene_010"

## Reawakening notes (per scene dormant >2 settimane)

Quando scena riprende dopo lungo silenzio (mesi), notes per re-onboarding:

- Tema chiave: <riassunto 1-frase>
- Char states emotional: Kazuki contemplative, Emiko on-edge
- Last cliffhanger: "the question hangs in the air"
- Estimated time-in-world passed: 12 ore (notte tra messaggio precedente e questo)

## Refs

- Lore: `[[creature_kitsune]]`, `[[geography_yamato_valley]]`
- Char sheets: `[[char_kazuki_takeda]]`, `[[char_emiko_yamashiro]]`
- Scene history: `[[scene_001_yamato_temple]]` (lead-in)
