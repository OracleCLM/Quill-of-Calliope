# OBLITERATUS workflow per Calliope.AI Tier 4b

> Abliteration top censored models per uso uncensored alta-qualità in scene sensibili.

**Status**: PLAN. Esecuzione P2 future (post-MVP M1-M3).

## OBLITERATUS overview (recon 2026-05-16)

Tool: `~/Scrivania/OBLITERATUS/` (Pliny the Prompter / elder-plinius).

**Cosa fa**: precision liberation di refusal direction da activation space transformer. Mantiene capabilities. Surgical projection out.

**Pipeline 6-step**:
```
SUMMON   → load model + tokenizer
PROBE    → collect activations on restricted vs unrestricted prompts
DISTILL  → extract refusal directions via SVD
EXCISE   → surgically project out guardrail directions (norm-preserving)
VERIFY   → perplexity + coherence checks — confirm capabilities intact
REBIRTH  → save liberated model with full metadata
```

## Comandi base

### Local CLI
```bash
cd ~/Scrivania/OBLITERATUS
pip install -e .
obliteratus obliterate meta-llama/Llama-3.1-8B-Instruct --method advanced
```

### HuggingFace Spaces (raccomandato per modelli grossi)
- URL: https://huggingface.co/spaces/pliny-the-prompter/obliteratus
- Free ZeroGPU daily quota (con HF Pro account, ~$10/mese)
- Zero install
- Best per 70B+ models (NM CPU non basta)

### Colab notebook
- Free GPU T4 limited time
- Sufficient per 7B-13B abliteration
- Per 70B → A100 Pro subscription serve

## Top candidates per Calliope.AI Tier 4b

Modelli censored top-quality da abliteration:

| Model | Size | Quality literate | Setup cost | Calliope use |
|-------|------|------------------|------------|--------------|
| Qwen-2.5-72B-Instruct | 40GB Q4 | ★★★★★ | HF Spaces ZeroGPU | Scene complex |
| Llama-3.3-70B-Instruct | 40GB Q4 | ★★★★½ | HF Spaces ZeroGPU | Scene narrative dense |
| Mistral-Large-2411 | 70GB Q4 | ★★★★★ | HF Spaces/Colab Pro | Scene climax dark |
| Llama-3.1-8B-Instruct | 5GB Q4 | ★★★½ | NM local OK | Scene quick uncensored test |

## Workflow proposed per Calliope

### Stage 1 — Pilot small (NM-local)
1. Abliterate Llama-3.1-8B-Instruct local (NM CPU OK per 8B)
2. ~2-4h CPU run, output `Llama-3.1-8B-obliterated`
3. Import in Ollama: `ollama create Llama-3.1-8B-obliterated -f Modelfile`
4. Test su Calliope skill `calliope-draft-response` con tier=4b
5. Valuta quality vs Tier 4a (dolphin-mistral-7b nativo uncensored)

### Stage 2 — Upgrade large (HF Spaces o Colab)
Se Stage 1 quality acceptable ma vuoi salto qualità:
1. Account HF Pro ($10/mese)
2. Abliterate Qwen-2.5-72B-Instruct su HF Spaces ZeroGPU
3. Download GGUF Q4 ~40GB
4. Import in Ollama: serve macchina con 48GB+ RAM (NM 15GB no, SL 96GB sì)
5. Quando 70B necessario → routing Calliope a SL via SSH (NM mandate operator: SL "se necessario")

### Stage 3 — Fine-tune con tuoi messaggi storici (P3 future)
Post-abliteration, fine-tune LoRA su tuoi messaggi historical (Excel + ChatGPT export):
1. Extract operator-written drafts da history (filter IC only)
2. Train LoRA con Unsloth library (~2-4h SL GPU)
3. Output: `<base>-obliterated-calliope-lora.safetensors`
4. Style replica AUTO matches tuo voice literate

## Anti-pattern OBLITERATUS

1. **NO abliteration senza verify**: step VERIFY mandatory. Misurare perplexity + coherence checks. Reject se degrade >15%
2. **NO abliteration commerciale models** senza license check (alcuni HF model hanno restrizione redistribution)
3. **NO storage cluster shared abliterated models**: tienili local NM/SL, NO upload back to HF Hub (rispetta original model authors)

## Effort stimato

- Stage 1 pilot (8B local): 4-6h compute + 1-2h setup
- Stage 2 large (70B HF Spaces): 1-2h setup + ZeroGPU quota wait + download 40GB
- Stage 3 fine-tune LoRA (P3): 6-10h (Unsloth + training + integration)

Total OBLITERATUS Calliope integration: 12-20h dev across stages.

## Privacy note

Abliterated models = local-only. NO upload back to HF Hub (rispetta upstream license + tua privacy). NO Discord post-image generata da abliterated model (rispetta TOS giocatori altri se sono in scene).

## Refs

- OBLITERATUS repo local: `~/Scrivania/OBLITERATUS/`
- HF Spaces: https://huggingface.co/spaces/pliny-the-prompter/obliteratus
- Paper: Arditi et al. 2024 "Refusal in Language Models Is Mediated by a Single Direction" https://arxiv.org/abs/2406.11717
- Gabliteration: https://arxiv.org/abs/2512.18901
