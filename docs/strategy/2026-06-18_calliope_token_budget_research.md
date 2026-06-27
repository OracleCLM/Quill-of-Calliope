---
title: Calliope — Token-Budget del blocco-contesto permanente (ricerca + proposta)
date: 2026-06-18
sprint: R-CALLIOPE-R-CAP-RESEARCH
mcp_assisted: yes
mcp_provider: WebSearch (ricerca esterna) + Read (ricerca JanitorAI esistente)
mcp_tool: WebSearch, WebFetch, Read
status: research-only (NESSUNA implementazione — solo proposta, gate nic)
tags: [calliope, token-budget, context-window, lost-in-the-middle, ruler, nolima, cap-adattivo, gateway]
---

# Calliope — Quanto deve essere grande il blocco-contesto permanente?

> Deliverable per nic. Domanda: come fissare il **TOKEN-BUDGET** del blocco permanente
> (schede char-attivi + lore key-match + char_memory) che alimenta la generazione narrativa.
> Decisione da prendere: **CAP FISSO** vs **CAP ADATTIVO-PER-MODELLO** (tetto come % del
> context-window oltre cui le risposte degradano).
> NON implemento il cap qui — solo ricerca evidence-based + schema-proposta.
>
> Tool usati: `WebSearch` (5 query: Lost-in-the-Middle, RULER, NoLiMa, per-modello,
> serving-provider), `Read` (ricerca JanitorAI esistente nel vault).

---

## 0. TL;DR — raccomandazione in una riga

**Adotta il CAP ADATTIVO-PER-MODELLO**, non il fisso. Permanent-cap = `context_window x
effective_factor x permanent_share`, con `effective_factor ≈ 0.5` (prudente, allineato a RULER)
e `permanent_share ≈ 0.35-0.40` del budget-effettivo riservato al blocco permanente. Per i
modelli del gateway Calliope questo dà cap pratici da **~5k (dolphin-mistral 32k)** a **~28k
(GLM-4.7 200k)** permanent token — molto sopra il vincolo JanitorAI da 8k-context, ma con la
**stessa regola-% sotto**. Il cap-fisso da 2.5k (lezione JanitorAI) resta valido come
*floor minimo* di sicurezza, non come tetto.

---

## 1. Ricerca — il context lungo NON è gratis (lost-in-the-middle & effective-context)

### 1.1 Lost in the Middle (Liu et al., 2023/2024 — TACL)

I modelli **non** usano in modo uniforme un context lungo. Liu et al. mostrano, su QA
multi-documento e key-value retrieval, una **curva di prestazione a U**: l'accuratezza è massima
quando l'informazione rilevante sta **all'inizio o alla fine** del context, e **degrada
significativamente quando sta nel mezzo** — anche per modelli esplicitamente "long-context".
Il calo è legato al superamento delle lunghezze viste in training: dentro la lunghezza di
training i modelli sono robusti, oltre compare la U.
[Fonte: arXiv 2307.03172 / TACL 2024]

> **Implicazione per Calliope**: più gonfi il blocco permanente, più materiale finisce "nel
> mezzo" e perde peso effettivo. Schede char-attivi e istruzioni-chiave vanno tenute **corte e
> ai bordi** (system in testa, post-history-instructions in coda), non annegate.

### 1.2 RULER (Hsieh et al., NVIDIA 2024) — effective ≪ claimed

RULER va oltre il needle-in-a-haystack: 13 task in 4 categorie (retrieval, variable-tracking,
aggregation, QA). Introduce il concetto di **effective context length** = la massima lunghezza
in cui il modello supera una soglia di passaggio (baseline Llama-2-7B @ 4k). Risultati:

- **La maggior parte dei modelli open ha effective context < 50% della lunghezza di training.**
- **Tutti** i modelli degradano all'aumentare della sequenza; anche GPT-4 (il migliore) perde
  ~15 punti passando da 4k a 128k.
- Stime aggregate: effective ≈ **50-65%** del dichiarato su molti modelli.
- Llama-3.1-70B: effective ~64k a fronte di 128k dichiarati (≈50%).

[Fonti: arXiv 2410.18745 "Why Does the Effective Context Length Fall Short?"; RULER via Medium/AI21;
Command A paper arXiv 2504.00698 per i punteggi Llama-3.1-70B su lunghezze crescenti]

### 1.3 NoLiMa (Modarressi et al., ICML 2025) — il caso peggiore (no literal-match)

NoLiMa rimuove l'overlap lessicale tra domanda e "needle" (serve inferenza, non matching
letterale) — più vicino al retrieval narrativo reale di Calliope (la scheda dice "timido", il
prompt chiede un comportamento, niente parola-chiave condivisa). Su 13 modelli con context
dichiarato ≥128k:

- **A 32k token, 11 modelli su 13 scendono sotto il 50%** del loro baseline a context corto.
- Cali **già visibili a 2k-8k token**.
- Anche GPT-4o: da 99.3% (corto) a 69.7%.

[Fonte: arXiv 2502.05167 / ICML 2025]

> **Implicazione**: per task narrativi che richiedono inferenza (non keyword-lookup), la
> degradazione è **anticipata** rispetto a RULER. Conferma di tenere `effective_factor`
> **prudente (~0.5)**, non ottimistico.

### 1.4 Sintesi della letteratura

| Benchmark | Cosa misura | Risultato-chiave | Soglia degrado pratica |
|---|---|---|---|
| Lost-in-Middle | uso posizionale | curva-U, mezzo penalizzato | info-chiave ai bordi |
| RULER | retrieval/reasoning multi-task | effective ~50-65% del claimed | usa ~50% come budget |
| NoLiMa | inferenza senza literal-match | −50% già a 32k su 11/13 modelli | inferenza degrada prima |

**Regola operativa**: il "vero" context utilizzabile per qualità narrativa stabile è circa
**metà** del context-window dichiarato. Il blocco-permanente deve stare dentro una **frazione**
di quel budget-effettivo, non riempirlo (deve lasciar spazio a history-scena + risposta).

---

## 2. Per-modello — gateway Calliope (context dichiarato + effective stimato)

| Modello (provider) | Context dichiarato | Effective stimato | Base stima |
|---|---|---|---|
| `zai-glm-4.7` (cerebras) | **200k** | ~100k (×0.5) | GLM-4.7 dichiara 200k; nessun RULER pubblico → stima per-claim ×0.5 (DICHIARATA) |
| `gpt-oss-120b` (cerebras) | **128k** (131072) | ~64k (×0.5) | RoPE 128k nativo; sliding-window+sink → stima famiglia ×0.5 (DICHIARATA) |
| `llama-3.3-70b-versatile` (groq) | **128k** (out 33k) | ~64k | RULER su Llama-3.1-70B (stessa arch): effective ~64k MISURATO |
| `deepseek-r1` (openrouter) | **128k** (130k R1-0528) | ~64k (×0.5) | 128k dichiarato; reasoning-model, nessun RULER diretto → stima ×0.5 (DICHIARATA) |
| `qwen3-coder` (openrouter) | **fino a 1M** | ~128-256k (×0.25 su long) | coding-model, claim 1M non verificato RULER → stima MOLTO conservativa (DICHIARATA) |
| `dolphin-mistral:7b` (ollama) | **32k** | ~16k (×0.5) | Mistral-7B v0.2/v0.3 base 32k reale; 7B piccolo → effective ~metà (DICHIARATA) |

Note: `out 33k` su groq = il tetto di **output** va sottratto dal budget (response-reserve, §3).
I valori "DICHIARATA" sono stime per-famiglia/size in assenza di RULER pubblico sul modello esatto;
solo Llama (via 3.1-70B) ha un dato misurato. Trattali come ordini-di-grandezza, non come verità.

---

## 3. Confronto con la lezione JanitorAI (regola assoluta vs regola-%)

Dalla ricerca esistente (`2026-06-18_calliope_janitorai_redesign_research.md` §1.1): JanitorAI
raccomanda **<2000-2500 permanent token** su un context JLLM **~8k** → cioè **≈30%** del context.

Punto cruciale: la cifra "2.5k" **non è universale**, è il **30% di 8k**. La vera lezione non è
il numero assoluto ma la **regola-percentuale** + la distinzione permanent-vs-cosmetico:

| Lettura | Numero | Generalizza? |
|---|---|---|
| Cap FISSO letterale | 2.5k token | NO — sprecherebbe il 99% di un context da 200k |
| Regola-% (la vera lezione) | ~30% del context **utile** | SÌ — è già un cap-adattivo travestito |

Quindi JanitorAI **conferma il cap-adattivo**: 2.5k era semplicemente `8k × ~0.30`. Su Calliope,
con context da 32k-200k, la stessa regola-% dà cap molto più alti — ma con lo **stesso principio**.
Il 2.5k va però conservato come **floor minimo**: sotto quella soglia una scena multi-char con
lore non ci sta comunque, indipendentemente dal modello.

---

## 4. Proposta — CAP FISSO vs CAP ADATTIVO

### 4.1 Opzione A — CAP FISSO (es. 2.5k permanent, uguale per tutti)

**Pro**: semplicissimo (una costante); prevedibile; nessuna tabella da mantenere; sicuro sul
modello più piccolo (dolphin 32k).
**Contro**: **spreca** i modelli grandi (2.5k su GLM-4.7-200k = usi l'1.25% del budget utile,
butti via 25 schede-char di headroom); rischia di **tagliare troppo** scene multi-char ricche
quando il modello potrebbe reggerle benissimo; non scala col gateway (aggiungere un modello 1M
non cambia nulla → inefficienza strutturale).

### 4.2 Opzione B — CAP ADATTIVO-PER-MODELLO (raccomandato)

Formula:
```
budget_effettivo   = context_window × effective_factor          # quanto il modello usa bene
permanent_cap      = budget_effettivo × permanent_share         # quota al blocco permanente
response_reserve   = max(min_out, budget_effettivo × resp_share) # spazio garantito alla risposta
history_budget     = budget_effettivo − permanent_cap − response_reserve  # resto = scena
```
Con valori-default proposti: `effective_factor = 0.5`, `permanent_share = 0.38`,
`resp_share = 0.15` (floor `min_out = 1500` token), `permanent_cap` **non sotto il floor 2.5k**.

**Pro**: scala col modello; rispetta la fisica (lost-in-middle/RULER) restando nella metà-utile;
sfrutta i context grandi senza annegare l'informazione-chiave; una sola formula, zero costanti
per-modello hardcoded (la tabella è solo `context_window`).
**Contro**: una tabella/funzione in più da mantenere; `effective_factor` è una stima (mitigato:
parti prudente 0.5, alza solo con evidenza); va testato il troncamento.

### 4.3 Tabella cap-adattiva concreta (valori suggeriti)

`effective_factor=0.5`, `permanent_share=0.38`, `resp_share=0.15`, floor permanent=2.5k.

| Modello | ctx_window | budget_eff (×0.5) | permanent_cap (×0.38) | response_reserve | history_budget |
|---|---|---|---|---|---|
| dolphin-mistral:7b | 32k | 16k | **~6.0k** | ~2.4k | ~7.6k |
| llama-3.3-70b (groq) | 128k | 64k | **~24k** | ~9.6k (cap out 33k ok) | ~30k |
| gpt-oss-120b | 128k | 64k | **~24k** | ~9.6k | ~30k |
| deepseek-r1 | 128k | 64k | **~24k** (vedi nota R1) | ~9.6k | ~30k |
| zai-glm-4.7 | 200k | 100k | **~38k** | ~15k | ~47k |
| qwen3-coder | 1M (cap a 256k) | 128k | **~49k** | ~19k | ~60k |

Nota **reasoning-model (deepseek-r1)**: il modello consuma context anche per i token di
*thinking*. Per R1 alza `resp_share` a ~0.25 (riserva il ragionamento) → permanent_cap effettivo
più prudente (~20k). Per qwen3-coder cappare il claim-1M a un effective realistico (es. 256k) per
non costruire prompt giganti e lenti che comunque degradano.

### 4.4 Strategia di troncamento (quando si supera il permanent_cap)

Priorità di conservazione (taglia dal basso verso l'alto), **troncamento graduale** non on/off:

```
1. SCHEDE CHAR-ATTIVI IN SCENA   → priorità MAX, mai droppate per intero.
   Se non entrano: comprimi (description→summary), poi droppa i char meno-recenti-a-parlare.
2. LORE KEY-MATCH (triggered_entries) → ordina per score-match desc; tieni i top-k che entrano,
   droppa i match deboli per primi.
3. CHAR_MEMORY (memoria persistente char) → priorità MIN; tieni le N entry più recenti/salienti,
   tronca lo storico vecchio per primo.
```
Regola posizionale (lost-in-middle): metti **system/istruzioni-chiave in testa** e
**post-history-instructions in coda**; il materiale-bulk (lore, memoria) **nel mezzo**, dove la
perdita di peso fa meno danno. Emetti un **warn/telemetria** quando scatta il troncamento (così
nic vede se un modello è cronicamente sotto-budget per le sue scene).

---

## 5. Raccomandazione finale per Calliope

1. **Adotta il CAP ADATTIVO-PER-MODELLO** (Opzione B). Il fisso spreca i modelli grandi e
   strozza le scene ricche; il cap-fisso 2.5k JanitorAI era già `8k×0.30`, cioè un adattivo.
2. **Parametri di partenza prudenti**: `effective_factor=0.5` (allineato RULER/NoLiMa),
   `permanent_share=0.38`, `resp_share=0.15`, **floor permanent = 2.5k** (sicurezza JanitorAI).
3. **Tabella minima da mantenere**: solo `{modello → context_window}` + override puntuali
   (R1 reasoning-reserve ↑, qwen3 cap-claim a 256k). Tutto il resto è formula.
4. **Override-per-modello dove c'è dato MISURATO**: per llama-3.3 (via 3.1-70B RULER) l'effective
   ~64k è reale → puoi tenere ×0.5 con fiducia. Per gli altri è stima: non superare ×0.5 finché
   non hai un benchmark proprio.
5. **Troncamento graduale prioritizzato** (char-attivi > lore-match > char_memory) + posizione
   ai-bordi per l'informazione-chiave + telemetria sui tagli.
6. **Validazione futura (non ora)**: una mini-suite needle-in-scene per misurare l'effective
   reale dei modelli del gateway sulle scene-tipo di Calliope → poi calibri `effective_factor`
   per-modello con dati propri invece di stime ×0.5.

> Gate nic: questa è **solo la proposta**. Implementazione (formula, tabella, troncamento) in uno
> sprint separato, previa approvazione dei valori-default sopra.

---

## Fonti

- Liu et al., "Lost in the Middle: How Language Models Use Long Contexts" — https://arxiv.org/abs/2307.03172 (TACL 2024)
- Hsieh et al., "RULER" + "Why Does the Effective Context Length of LLMs Fall Short?" — https://arxiv.org/html/2410.18745v1
- Modarressi et al., "NoLiMa: Long-Context Evaluation Beyond Literal Matching" — https://arxiv.org/abs/2502.05167 (ICML 2025)
- Command A paper (Llama-3.1-70B RULER scores) — https://arxiv.org/pdf/2504.00698
- Groq Llama-3.3-70B-Versatile model card (128k ctx, 33k out) — https://console.groq.com/docs/model/llama-3.3-70b-versatile
- gpt-oss-120b (128k/131072) — https://openai.com/index/introducing-gpt-oss/
- DeepSeek-R1 (128k) — https://github.com/deepseek-ai/DeepSeek-R1
- GLM-4.7 (200k) — https://unsloth.ai/docs/models/glm-4.7
- dolphin-mistral 7B (32k, Mistral-7B v0.2/v0.3 base) — https://ollama.com/library/dolphin-mistral
- Ricerca interna JanitorAI (regola <2-2.5k / ~30% di 8k) — vault `060_PROJECTS/Calliope/2026-06-18_calliope_janitorai_redesign_research.md` §1.1
