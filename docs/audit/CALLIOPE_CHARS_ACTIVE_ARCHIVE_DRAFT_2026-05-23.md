# Calliope Chars — Active / Archive classification draft

**Date**: 2026-05-23
**Sprint**: R-CALLIOPE-CHARS-ACTIVE-ARCHIVE-CLASSIFY-DRAFT
**Per**: nic (operator)

## Come usare questo file

Auto-classificazione iniziale:
- **ATTIVI** = char con entry esistente in `char_memory.db` (qualcuno o qualcosa li ha già indicizzati)
- **ARCHIVIO** = char con file `.yaml` su disco MA senza entry DB (probabilmente NPC minori, draft non finiti, archivio storico)
- **DB-only** = char presenti in DB MA senza file `.yaml` su disco (anomalia da risolvere — name mismatch o yaml mancante)

**Edit manuale**: sposta entry tra le 2 liste (attivi/archivio) mettendo o togliendo `[x]`. Operatore può tagliare/incollare voci tra sezioni se la classificazione automatica è sbagliata.

Quando finito, segnala a Claude: il file sarà processato per popolare un campo `active: true/false` in ogni yaml + ri-popolare `char_memory.db` con i nuovi attivi.

---

## ATTIVI — auto-classified (20)

Char con entry in `char_memory.db`. Restano attivi salvo override operatore (rimuovi `[x]` per spostare in archivio).

- [x] **arianna** — `characters/arianna.draft.yaml`
- [x] **aurora** — `characters/aurora.draft.yaml`
- [x] **azu-blythe** — `characters/azu-blythe.draft.yaml`
- [x] **cassandra-blythe** — `characters/cassandra-blythe.draft.yaml`
- [x] **clover** — `characters/clover.draft.yaml`
- [x] **filomena** — `characters/filomena.draft.yaml`
- [x] **ira** — `characters/ira.draft.yaml`
- [x] **kikyo** — `characters/kikyo.draft.yaml`
- [x] **koibo** — `characters/koibo.draft.yaml`
- [x] **mirko** — `characters/mirko.draft.yaml`
- [x] **narrator** — `characters/narrator.draft.yaml`
- [x] **nikita** — `characters/nikita.draft.yaml`
- [x] **pdor** — `characters/pdor.draft.yaml`
- [x] **peaches** — `characters/peaches.draft.yaml`
- [x] **philip-annabelle** — `characters/philip-annabelle.draft.yaml`
- [x] **alexis-snyder** — `characters/private/alexis-snyder.yaml`
- [x] **narrator** — `characters/private/narrator.yaml`
- [x] **syvis** — `characters/syvis.draft.yaml`
- [x] **viola** — `characters/viola.draft.yaml`
- [x] **yan-qing** — `characters/yan-qing.draft.yaml`

---

## ARCHIVIO — auto-classified (102)

Char con file yaml su disco MA senza entry in `char_memory.db`. Marcabili come attivi inserendo `[x]`.

- [ ] TEMPLATE — `characters/TEMPLATE.yaml`
- [ ] alexis-snyder.canon — `characters/alexis-snyder.canon.yaml`
- [ ] andra — `characters/private/andra.yaml`
- [ ] apollyon — `characters/private/apollyon.yaml`
- [ ] arianna-exilio-the-fiery — `characters/private/arianna-exilio-the-fiery.yaml`
- [ ] arryn-wranwarin — `characters/private/arryn-wranwarin.yaml`
- [ ] art — `characters/private/art.yaml`
- [ ] aster — `characters/private/aster.yaml`
- [ ] aurelius-astra — `characters/private/aurelius-astra.yaml`
- [ ] aurora-of-winter — `characters/private/aurora-of-winter.yaml`
- [ ] benkei-boron — `characters/private/benkei-boron.yaml`
- [ ] blake — `characters/private/blake.yaml`
- [ ] bredgolds-roster — `characters/private/bredgolds-roster.yaml`
- [ ] bubs — `characters/private/bubs.yaml`
- [ ] cousin-fech — `characters/private/cousin-fech.yaml`
- [ ] creepy-creeper — `characters/private/creepy-creeper.yaml`
- [ ] dante — `characters/private/dante.yaml`
- [ ] derrick-randolf — `characters/private/derrick-randolf.yaml`
- [ ] dr-arthur-left — `characters/private/dr-arthur-left.yaml`
- [ ] e5k1m0s-characters — `characters/private/e5k1m0s-characters.yaml`
- [ ] fernándo-igrys — `characters/private/fernándo-igrys.yaml`
- [ ] filomena-exilio-cold-wind — `characters/private/filomena-exilio-cold-wind.yaml`
- [ ] friaginleif-fria — `characters/private/friaginleif-fria.yaml`
- [ ] friedrich-fede-zann — `characters/private/friedrich-fede-zann.yaml`
- [ ] frybol — `characters/private/frybol.yaml`
- [ ] garaph-gabby-elbriel — `characters/private/garaph-gabby-elbriel.yaml`
- [ ] geo-changer — `characters/private/geo-changer.yaml`
- [ ] grimm — `characters/private/grimm.yaml`
- [ ] harmony-tremblay — `characters/private/harmony-tremblay.yaml`
- [ ] haruki-ansel-final — `characters/private/haruki-ansel-final.yaml`
- [ ] haruki-ansel — `characters/private/haruki-ansel.yaml`
- [ ] idref-nigimag — `characters/private/idref-nigimag.yaml`
- [ ] ira-nigimag — `characters/private/ira-nigimag.yaml`
- [ ] ivan-borisovich — `characters/private/ivan-borisovich.yaml`
- [ ] ivis-shirley — `characters/private/ivis-shirley.yaml`
- [ ] keskior-and-fenrir — `characters/private/keskior-and-fenrir.yaml`
- [ ] kyro — `characters/private/kyro.yaml`
- [ ] lantern-bringer — `characters/private/lantern-bringer.yaml`
- [ ] liora-and-nyx — `characters/private/liora-and-nyx.yaml`
- [ ] lira-vesper — `characters/private/lira-vesper.yaml`
- [ ] lucas — `characters/private/lucas.yaml`
- [ ] luki — `characters/private/luki.yaml`
- [ ] luna — `characters/private/luna.yaml`
- [ ] lyra — `characters/private/lyra.yaml`
- [ ] mama-volta — `characters/private/mama-volta.yaml`
- [ ] mato-el-gato — `characters/private/mato-el-gato.yaml`
- [ ] maxwell — `characters/private/maxwell.yaml`
- [ ] melka-the-dark-priest — `characters/private/melka-the-dark-priest.yaml`
- [ ] mercenary-disgraced-ex-knight — `characters/private/mercenary-disgraced-ex-knight.yaml`
- [ ] midwife — `characters/private/midwife.yaml`
- [ ] military-weapon — `characters/private/military-weapon.yaml`
- [ ] musashi — `characters/private/musashi.yaml`
- [ ] nathan-explosion — `characters/private/nathan-explosion.yaml`
- [ ] natse — `characters/private/natse.yaml`
- [ ] npc-2 — `characters/private/npc-2.yaml`
- [ ] npc-3 — `characters/private/npc-3.yaml`
- [ ] npc-4 — `characters/private/npc-4.yaml`
- [ ] npc-5 — `characters/private/npc-5.yaml`
- [ ] npc — `characters/private/npc.yaml`
- [ ] oc-template-suggestion — `characters/private/oc-template-suggestion.yaml`
- [ ] orkadia-susie — `characters/private/orkadia-susie.yaml`
- [ ] papa-gromp — `characters/private/papa-gromp.yaml`
- [ ] pdor-son-of-kmer — `characters/private/pdor-son-of-kmer.yaml`
- [ ] phillip-philly-annabelle — `characters/private/phillip-philly-annabelle.yaml`
- [ ] pickles — `characters/private/pickles.yaml`
- [ ] remina-inferno — `characters/private/remina-inferno.yaml`
- [ ] revek — `characters/private/revek.yaml`
- [ ] roger — `characters/private/roger.yaml`
- [ ] rosa — `characters/private/rosa.yaml`
- [ ] ruby-blight — `characters/private/ruby-blight.yaml`
- [ ] rusty — `characters/private/rusty.yaml`
- [ ] ruth — `characters/private/ruth.yaml`
- [ ] sberla — `characters/private/sberla.yaml`
- [ ] scp-023-black-shuck — `characters/private/scp-023-black-shuck.yaml`
- [ ] scp-682-hard-to-destroy-reptile — `characters/private/scp-682-hard-to-destroy-reptile.yaml`
- [ ] scp-999-the-tickle-monster — `characters/private/scp-999-the-tickle-monster.yaml`
- [ ] semmis-characters — `characters/private/semmis-characters.yaml`
- [ ] semmis-npcs — `characters/private/semmis-npcs.yaml`
- [ ] sir-matthew-schatten — `characters/private/sir-matthew-schatten.yaml`
- [ ] sister-elsbeth-vaelwyn — `characters/private/sister-elsbeth-vaelwyn.yaml`
- [ ] skisgaar-skwigelf — `characters/private/skisgaar-skwigelf.yaml`
- [ ] syvis-luyra — `characters/private/syvis-luyra.yaml`
- [ ] takeshi-seiso — `characters/private/takeshi-seiso.yaml`
- [ ] tamura-yorend — `characters/private/tamura-yorend.yaml`
- [ ] the-judge-the-jury-and-the-executioner-tarmek — `characters/private/the-judge-the-jury-and-the-executioner-tarmek.yaml`
- [ ] the-lamb — `characters/private/the-lamb.yaml`
- [ ] the-warlord-of-maikadirr — `characters/private/the-warlord-of-maikadirr.yaml`
- [ ] throll — `characters/private/throll.yaml`
- [ ] ticket-seller — `characters/private/ticket-seller.yaml`
- [ ] toki-wartooth — `characters/private/toki-wartooth.yaml`
- [ ] town-guard — `characters/private/town-guard.yaml`
- [ ] trekka — `characters/private/trekka.yaml`
- [ ] trekken — `characters/private/trekken.yaml`
- [ ] uncle-borg — `characters/private/uncle-borg.yaml`
- [ ] vanefa-teufelsjäger — `characters/private/vanefa-teufelsjäger.yaml`
- [ ] vision-characters-final-no-talking — `characters/private/vision-characters-final-no-talking.yaml`
- [ ] visions-characters — `characters/private/visions-characters.yaml`
- [ ] william-murderface — `characters/private/william-murderface.yaml`
- [ ] yuki-copycat — `characters/private/yuki-copycat.yaml`
- [ ] ŝandra — `characters/private/ŝandra.yaml`
- [ ] saturn — `characters/saturn.draft.yaml`
- [ ] silver — `characters/silver.draft.yaml`

---

## DB-ONLY anomaly (1)

Char presenti in `char_memory.db` MA senza file `.yaml` corrispondente. Possibili cause: rename, yaml mai creato, name normalization mismatch. Da indagare separatamente.

- ⚠ `Full Name` (nessun yaml su disco)

---

## Stats

- Total yaml su disco: 122
- Total char in DB: 20
- Attivi auto (yaml + DB match): 20
- Archivio auto (yaml only): 102
- DB-only anomalies: 1
- Coverage: 20/122 yaml attivi (16%)

_Generated 2026-05-23 by orch-calliope (self-execute)._
