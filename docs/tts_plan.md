# Quill of Calliope — TTS plan

## v1.1 — Minimal English single voice (2026-05-17, M3 sprint)

**Status**: IMPLEMENTED — `scripts/tts_speak.py`

### Operator-spec (verbatim TG 19:16)
> "lo userei solo quando non voglio leggere ma ascoltare" — passive listening, hands-free.

### Decision: minimal single English voice
- **Multi-voice per chars**: deferred indefinitely (operator-spec 2026-05-17)
- **Voice cloning**: deferred (Coqui XTTS-v2, M5+)
- **Use case**: listen to scene drafts via headphones/speaker

### Engine chosen: pyttsx3 + espeak-ng (primary)

**Rationale**: zero-setup (already installed on NM), 131 EN voices available,
WAV output 22050Hz 16-bit mono, synthesis time ~0.01s short / ~0.03s long,
no model download required. Piper TTS installed (`/tmp/calliope_venv/`) as upgrade
path when en_US-amy-medium model downloaded (~63MB).

**Known limitation**: pyttsx3 must use singleton engine per process (re-init = 0-byte WAV).
`tts_speak.py` handles this with `_pyttsx3_engine` module-level singleton.

### Sample output (verified)
| File | Size | Duration approx |
|------|------|----------------|
| Short (1 sentence) | 106 KB | ~3s |
| Long (7 sentences) | 827 KB | ~23s |
| Special chars | 223 KB | ~6s |

### CLI
```bash
# Play immediately
echo "The blade remembers what the heart forgets." | python scripts/tts_speak.py

# Save to WAV
python scripts/tts_speak.py --text "Aurora raised her hand." --output /tmp/scene.wav

# Speed up
python scripts/tts_speak.py --text "..." --rate 1.2 --output /tmp/fast.wav
```

### Integration: route_scene.py --speak (stub)
```bash
python scripts/route_scene.py --scene-type lore_exposition --speak
# → [--speak stub] Would speak: scene_type=lore_exposition ... → openrouter_reasoning
```
Real scene text integration pending scene-gen sprint.

---

# Quill of Calliope — TTS plan (M5 feature — full vision)

> Text-to-speech narration con punteggiatura-aware + per-char voice profile. Operator listen audio drafts mentre cammina/cucina.

**Status**: PLAN M5 (post-CLI funzionante). Implementation post-MVP M1-M3.

## Motivation operator (2026-05-16)

- Long sessioni RP → drafts importanti vorrebbe ascoltarli multitasking
- Punteggiatura ha SIGNIFICATO nel suo stile (timing pause, emphasis, breath)
- Per-char voice = chars distinti suonano differenti (immersione)
- Replicate punteggiatura "metodo personale" + variazione per altri giocatori

## TTS engine candidates

### Tier 1 — Piper TTS (raccomandato per MVP TTS)

**Pros**:
- Offline 100% local (privacy NM-only)
- Ultra-lightweight (~50MB models, real-time CPU inference)
- Multi-voice premade libreria (>100 voices EN)
- ONNX inference, fast su CPU NM
- Python API + CLI

**Cons**:
- Voice cloning limited (premade only, no quick personal voice clone)
- Punteggiatura interpretation moderate (better-than-naive but no semantic emphasis)

**Setup**:
```bash
pip install piper-tts
# Download voice models
piper-voice-download en_US-amy-medium
piper-voice-download en_GB-alan-medium  # for Kazuki?
piper-voice-download en_US-libritts_r-medium  # multi-voice
```

**Usage**:
```bash
echo "The blade remembers what the heart forgets." | piper \
  --model en_US-amy-medium.onnx \
  --output_file /tmp/output.wav
```

### Tier 2 — Coqui XTTS-v2 (advanced, future P3)

**Pros**:
- Multi-lingual support (EN/IT/FR/JP) → utile se char parlano italiano-flavored o lingue diverse
- Voice cloning da 6-second sample (operator può clonare suo voice se vuole)
- Higher quality vs Piper
- Active community

**Cons**:
- Heavier (~1GB model + dependencies)
- GPU recommended per real-time (CPU OK ma lento)
- Commercial license restrictions (verify per use case)

### Tier 3 — Kokoro-82M (hot 2026, ultraleggero)

**Pros**:
- 82M params only, super-leggero
- EN-only ma top quality per size
- Hugging Face hosted, Apache-2.0 license
- Fast inference CPU

**Cons**:
- New (2026), community ancora piccola
- EN-only

**Recommended approach**: start Piper TTS (MVP M5), evaluate Kokoro-82M post-test, upgrade Coqui solo se voice cloning serve.

## Punteggiatura interpretation strategy

### Operator personal style — analisi statistica

Step 1 — Extract operator messages da Yokai.xls + Discord history:
```python
# Filtra solo messaggi operator (player=nic)
operator_messages = filter_messages(history, player="nic")
```

Step 2 — Analisi pattern punteggiatura:
- Word count per sentence (avg/median/p95)
- Comma frequency (commas per sentence)
- Period vs ellipsis vs em-dash usage
- Italic/bold markdown usage (emphasis)
- CAPS usage (shouting/emphasis)
- Paragraph break frequency

Step 3 — Output `your_punctuation_signature.yaml`:
```yaml
operator: nic
analyzed_messages: 2531
analysis_date: 2026-05-16
metrics:
  sentence_length:
    avg_words: 18.3
    median: 16
    p95: 38
  punctuation_density:
    commas_per_sentence: 2.4
    periods_per_para: 4.1
    ellipsis_freq: 0.15  # 15% of sentences end with ...
    em_dash_freq: 0.22
  emphasis:
    italic_per_para: 1.8
    bold_rare: true
    caps_only_significant: true  # CAPS = shouting
  pacing:
    short_sentences_pct: 22  # < 8 words = punchy
    long_sentences_pct: 18  # > 30 words = lyrical
  vocabulary:
    avg_complexity: high  # Flesch-Kincaid grade ~12
    archaic_freq: 0.08
```

Step 4 — TTS config mapping:
```python
# piper-tts config
tts_config = {
    "comma_pause_ms": 400,  # operator uses commas heavily
    "period_pause_ms": 800,
    "ellipsis_pause_ms": 1200,  # dramatic pause
    "em_dash_pause_ms": 600,
    "italic_emphasis_pitch": +5,  # subtle
    "caps_emphasis_volume": +3,
    "paragraph_break_pause_ms": 1500,
}
```

### Per-character voice profile

Per ogni char (PC + NPC), assegnare voice TTS distinta:

```yaml
# characters/kazuki_takeda.yaml (extension)
tts:
  voice_model: en_GB-alan-medium  # measured British
  pitch_shift: -2  # baritone
  speed: 0.95  # slightly slow
  emotion_default: contemplative
```

```yaml
# characters/queen_aurora.yaml
tts:
  voice_model: en_US-libritts_r-female-imperious
  pitch_shift: +1
  speed: 1.0
  emotion_default: regal
```

```yaml
# characters/npc_merchant.yaml
tts:
  voice_model: en_US-libritts_r-male-warm
  pitch_shift: 0
  speed: 1.1  # bit faster, energetic
  emotion_default: friendly
```

### Other players style detection (optional)

Se vuoi replicare punteggiatura altri giocatori (per dialoghi multipli letti):
- Analisi statistica per ogni player_id distinto
- Output `player_<id>_punctuation.yaml` (anonimo se serve)
- TTS render per char alterna voce + applica pattern punteggiatura giocatore corrispondente

## CLI commands TTS (target M5)

```bash
calliope tts draft <draft_text_or_file> --voice auto  # auto = per-char voice
calliope tts read-scene <scene_id>  # legge ultima reply scena
calliope tts analyze-style --target operator  # genera punctuation_signature.yaml
calliope tts list-voices  # mostra voices disponibili
```

## Anti-pattern TTS

1. **NO TTS scene sensibili senza preview**: operator deve approvare draft prima di TTS render (audio rinforza errori)
2. **NO TTS lungo (>5000 char)**: chunk in paragraphs, TTS può lag se input gigante
3. **NO voice cloning senza consent** giocatori altri (privacy)

## Effort stimato

- Setup Piper TTS + 5 voice models: 1-2h
- Punctuation signature analyzer: 3-4h
- Per-char voice profile schema + config: 2-3h
- CLI commands TTS: 2-3h
- Test E2E + iterazioni quality: 4-6h
- **Total M5**: 12-18h (~2-3 giorni dev part-time, deferred post-MVP)
