# Quill of Calliope — Image generation plan (M5 feature, paired with TTS)

> Visual scene generation con char consistency cross-image. NSFW-capable per battle/horror scene narrative. NM-CPU OK (tempi lunghi tollerati).

**Status**: PLAN 2026-05-16. Reuse Vesta-Minerva infrastructure esistente.

## Vesta-Minerva integration (CRITICAL FINDING 2026-05-16)

Operator-correct: Vesta-Minerva HA già image gen infrastructure completa.

Componenti scoperti `~/Scrivania/Vesta/`:
- `Vesta/Minerva/image_gen.py` — AUTOMATIC1111 backend con `ImagePromptLayers` (checkpoint + lora_tag + quality_prefix + character_prompt + scene_prompt + negative_prompt)
- `Vesta/Minerva/model_registry.py` — `build_image_model_catalog()` con CivitAI checkpoints
- `Vesta/comfy_client.py` — ComfyUI alternative backend (più nodale, control fine)
- Test coverage: `Vesta/tests/test_comfy_client.py`

**Strategy Calliope**: import as library (Path A, da vesta_minerva_reuse_map.md). Adapt `ImagePromptLayers` per RP scene composition. Char references = LoRA per personaggio (trained o downloaded da CivitAI).

## Operator answers (2026-05-16)

| Q | Operator answer | Implication Calliope |
|---|----------------|---------------------|
| Q1 GPU | NM-only preferito, SL fallback se necessario. Tempi lunghi OK | CPU SDXL ~5-15min/image acceptable. NM workflow primary |
| Q2 Frequency | Solo su richiesta operator OR proposta CLI | On-demand only, no auto-gen post-scene |
| Q3 Style/multi-char | Char models propri + modelli multi-char compositi (input image + istruzioni) | IP-Adapter Plus + InstantID + ComfyUI workflow custom |
| Q4 NSFW/dark | NSFW OK (CivitAI default). Battle/horror/mild violence: model TBD | SDXL action checkpoints (vedi sotto) |
| Q5 Discord | NO direct integration MVP. Operator review/edit, manual post | Output local files, copia-incolla workflow |

## Stack tech proposto

### Backend WebUI (operator choice)
- **ComfyUI** (preferred): nodale, save workflow custom multi-char composition. Cache workflow per "scene 3 personaggi + battle background"
- AUTOMATIC1111: alternativa, già supportato da Vesta-Minerva
- Both reachable via Vesta `image_gen.py` adapter

### Base models SDXL

Per generic scene + char single:
- **SDXL base 1.0** — generalist
- **AnimagineXL 3.1** — anime style (Holo Spice and Wolf inspired Aurora!)
- **PonyDiffusion V6 XL** — anime + flexible NSFW + multi-char
- **JuggernautXL v11** — cinematic action realistic
- **DreamShaperXL** — versatile painterly

Per battle/horror/mild violence:
- **WildCardX-XL Animation** — anime action scenes
- **MeinaMix V11** — anime mix violence-capable
- **HassakuXL** — horror/dark fantasy capable
- **Pony Diffusion** (above) — flexible for combat scenes

### Multi-character composition

**IP-Adapter Plus** (HuggingFace): face transfer per char consistency. Reference image → embed → conditioning generation.

**InstantID** (Tencent): 1-shot face cloning, anche solo 1 reference image. Combinable con SDXL/SDXL-anime.

**PuLID** (ByteDance): face preservation higher fidelity, lightweight.

**OmniGen** (2026): single unified model, text + multi-image input. Multi-char scene generation in single forward pass. HOT 2026, ComfyUI integration emergente.

**ComfyUI workflow proposed**:
```
[Text Prompt: scene description]
        ↓
[SDXL checkpoint anime/realistic]
        ↓
[IP-Adapter #1: char1 reference image (Aurora)]
[IP-Adapter #2: char2 reference image (Kazuki)]
[IP-Adapter #3: char3 reference image (Emiko)]
        ↓
[ControlNet: pose/depth condition (optional)]
        ↓
[KSampler: 30-50 steps]
        ↓
[Output: 1024x1024 PNG]
```

Save as ComfyUI workflow JSON per re-use. Operator può triggerare via Calliope CLI.

### LoRA training char propri

Per personaggi operator core (Kazuki, Emiko, queen Aurora) può fare:
1. Training LoRA da 10-50 reference images (esistenti + variations)
2. Tool: Kohya_ss (popular LoRA trainer) o sd-scripts
3. Compute: SL RTX 4060 8GB sufficient per SDXL LoRA training (~1-2h)
4. Output: `<char>.safetensors` LoRA file, copiabile in `~/SDXL/loras/` per ComfyUI/A1111 access

Workflow operator (M5 future):
- Operator collect 20-50 images Aurora da Internet (Holo + variations)
- LoRA training SL GPU 1h
- `aurora-lora.safetensors` saved
- CLI invocation: `calliope image scene --char aurora --char kazuki --prompt "they share a quiet evening by the fire"` → IP-Adapter LoRA aurora + LoRA kazuki + scene → output image

### NSFW + battle/horror models

CivitAI checkpoint senza filter NSFW by default (most). Per scene:
- **Battle**: JuggernautXL + IP-Adapter char + ControlNet OpenPose (battle stance ref pose)
- **Horror dark**: HassakuXL + IP-Adapter char + ControlNet depth (creepy lighting)
- **Erotic** (se serve): Pony Diffusion V6 (popular NSFW capable, anime style fits Holo)

Operator-mandate: opt-in solo quando scena lo richiede. Default = safer checkpoint (AnimagineXL/DreamShaperXL).

## CLI commands image gen (target M5)

```bash
calliope image generate --prompt "<scene description>" --char <name> [--char <name2>] [--style <preset>]
calliope image train-lora --char <name> --images <dir>  # train LoRA from refs
calliope image upscale <output.png>  # 2x via Real-ESRGAN
calliope image list-checkpoints  # show available SDXL checkpoints
calliope image list-loras  # show trained char LoRAs
calliope image batch --scene <scene_id>  # generate 4-8 variations for scene
```

## Storage budget

Stima per char (training + generated):
- Reference images per LoRA: 50 × 1MB = 50MB
- Trained LoRA file: 150MB (SDXL LoRA size)
- Generated scenes: 4MB/image × 100/anno = 400MB

Per 5 char active: ~3GB. Total Quill of Calliope dir: 5-15GB realistic ongoing. Disk OK (operator 458GB total).

Backup: Discord backup-natural per drafts importanti. Local archive `datasets/generated/<year>/` se serve preserve, altrimenti ephemeral cleanup oltre 90 giorni.

## Effort stimato M5 (post-MVP)

- Vesta-Minerva import + adapt: 4-6h
- ComfyUI workflow multi-char + IP-Adapter setup: 4-6h
- Char LoRA training procedura + first LoRA (Aurora): 3-4h
- CLI commands image: 4-6h
- Documentation + examples: 2-3h
- **Total M5 image gen**: 17-25h dev (~2-3 giorni part-time)

Stessa magnitude TTS. M5 può essere "TTS + Image" combined milestone (~30-40h totali).

## Anti-pattern image gen

1. **NO API services** (Replicate/Together): NM-only operator-mandate
2. **NO auto-gen post-scene**: solo on-request (Q2 operator)
3. **NO LoRA training senza consent**: per char altri giocatori, NO LoRA training senza loro permesso
4. **NO Discord auto-post**: operator review/edit always

## Next steps

1. Document tracking image gen scope in VISION + MVP roadmap M5
2. Sprint dispatch quando M3 (CLI core) done: M5-image sprint (Vesta-Minerva import + ComfyUI setup + 1 char LoRA Aurora pilot)
3. Operator review M5 output → iterate quality + workflow refinement
