#!/usr/bin/env python3
"""Batch generate 15 Yokai RP scene samples (MD + WAV) via LLM routing gateway."""

import argparse
import json
import logging
import re
import sys
import time
from datetime import datetime
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from route_scene import dispatch_to_tier, load_config  # noqa: E402
from tts_speak import tts_speak_bilingual  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

SCENES = [
    (1,  "action_combat",         "cerebras_workhorse",    "Aurora deflects a corrupted yokai's strike, her graviturgy bending the creature's claws away as she calls to her allies."),
    (2,  "character_death",       "cerebras_workhorse",    "The healer Syvis closes the eyes of the fallen guardian, her voice steady though her hands tremble."),
    (3,  "romantic_fade_to_black","groq_fast",             "Philip Annabelle takes Aurora's hand under the moonlit cherry blossoms of the palace garden."),
    (4,  "lore_exposition",       "openrouter_reasoning",  "The NARRATOR speaks of the ancient Yokai treaty, three centuries of fragile peace between fox-kin and the mountain clans."),
    (5,  "action_aftermath",      "cerebras_workhorse",    "The battle square is silent now. Aurora kneels beside the shattered ward-stone, the price of victory plain on every face."),
    (6,  "comedic_banter",        "groq_fast",             "Koibo accidentally transforms into a teapot at the worst possible moment during an audience with the visiting ambassador."),
    (7,  "mystery_investigation", "openrouter_reasoning",  "Filomena finds a second set of footprints in the sealed treasury — none of the guards remember unlocking the door."),
    (8,  "exploration_landscape", "cerebras_workhorse",    "The party emerges from the Whispering Forest into a valley blanketed in snow-white fox-fire, silent and impossibly beautiful."),
    (9,  "intimate_dialogue",     "groq_fast",             "Aurora and Filomena sit by the dying hearth, speaking in low voices about the homes they left behind to serve the Crown."),
    (10, "transition_temporal",   "groq_fast",             "Three months passed. The cherry blossoms fell and rose again. When Narrator marks the new season, the guild's roster has changed."),
    (11, "flashback_memory",      "openrouter_reasoning",  "Aurora remembers the night her village burned — the smell of pine smoke, her mother's hand releasing hers in the crowd."),
    (12, "dream_surreal",         "cerebras_workhorse",    "In the dream Philip Annabelle walks a corridor where every door opens onto the same empty throne room, slightly closer each time."),
    (13, "ritual_ceremony",       "openrouter_reasoning",  "The Fox-Queen's coronation begins at moonrise: incense smoke, nine drums, the binding oath spoken in the old tongue."),
    (14, "combat_chase",          "cerebras_workhorse",    "Koibo sprints across the market rooftops, the stolen scroll under one arm, three guards and a very angry merchant in pursuit."),
    (15, "ooc_meta",              "groq_fast",             "The players pause the session to clarify whether the ward-stone explosion affects party members or only enemies."),
]


def generate_scene(num, scene_type, tier, seed, config, gateway_url) -> tuple:
    prompt = (
        f"Write a 2-3 paragraph RP scene for the Kingdom of Yokai tabletop RPG.\n"
        f"Scene type: {scene_type.replace('_', ' ')}\n"
        f"Starting prompt: {seed}\n\n"
        f"Write in immersive third-person fantasy prose. Keep it 150-250 words. Stay in character."
    )
    t0 = time.time()
    try:
        text = dispatch_to_tier(
            tier_name=tier, prompt=prompt, config=config,
            gateway_url=gateway_url, timeout=45, max_retries=2,
        )
        return text.strip(), time.time() - t0
    except Exception as exc:
        log.warning("Scene %02d (%s) failed: %s", num, scene_type, exc)
        return f"[Generation failed for {scene_type}: {exc}]", time.time() - t0


def save_scene_md(num, scene_type, tier, seed, text, latency, output_dir) -> Path:
    md = (
        f"---\nscene_num: {num:02d}\nscene_type: {scene_type}\ntier: {tier}\n"
        f'seed: "{seed[:80]}"\nlatency_sec: {latency:.2f}\nchars: {len(text)}\n'
        f"generated_at: {datetime.utcnow().isoformat()}Z\n---\n\n"
        f"# Scene {num:02d} — {scene_type.replace('_', ' ').title()}\n\n{text}\n"
    )
    path = output_dir / f"sample_{num:02d}_{scene_type}.md"
    path.write_text(md, encoding="utf-8")
    return path


def generate_wav(num, scene_text, audio_dir) -> Path:
    out = audio_dir / f"sample_{num:02d}.wav"
    clean = scene_text.strip()
    if clean.startswith("---"):
        parts = clean.split("---", 2)
        clean = parts[2].strip() if len(parts) >= 3 else clean
    clean = re.sub(r"^#+\s+.*$", "", clean, flags=re.MULTILINE).strip()
    try:
        tts_speak_bilingual(clean, output_path=str(out), rate=1.0, play=False)
    except Exception as exc:
        log.error("WAV failed scene %02d: %s", num, exc)
        out.write_bytes(b"")
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch generate Yokai scene samples + WAV")
    parser.add_argument("--gateway-url", default="http://localhost:8766")
    parser.add_argument("--output-dir", type=Path, default="scenes/m3_library_samples")
    parser.add_argument("--audio-dir", type=Path, default="scenes/m3_library_samples/audio")
    parser.add_argument("--config", type=Path, default="data/llm_routing_config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Skip LLM + TTS calls")
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.audio_dir.mkdir(parents=True, exist_ok=True)

    try:
        config = load_config(str(args.config))
    except Exception as exc:
        log.error("Config load failed: %s", exc)
        sys.exit(1)

    stats = []
    for num, scene_type, tier, seed in SCENES:
        log.info("[%02d/15] %s → %s", num, scene_type, tier)

        if args.dry_run:
            text, latency = f"[DRY RUN] Scene {num} {scene_type}.", 0.1
            wav_kb = 0
        else:
            text, latency = generate_scene(num, scene_type, tier, seed, config, args.gateway_url)
            save_scene_md(num, scene_type, tier, seed, text, latency, args.output_dir)
            wav = generate_wav(num, text, args.audio_dir)
            wav_kb = round(wav.stat().st_size / 1024) if wav.exists() else 0

        stats.append({"scene_num": num, "scene_type": scene_type, "tier": tier,
                      "latency_sec": round(latency, 2), "chars": len(text), "wav_kb": wav_kb})
        log.info("  latency=%.1fs chars=%d wav=%dKB", latency, len(text), wav_kb)

    stats_path = args.output_dir / "GENERATION_STATS.json"
    stats_path.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Done. Stats → %s", stats_path)
    # Summary
    ok = sum(1 for s in stats if s["chars"] > 50)
    print(f"\n✓ {ok}/15 scenes generated | avg latency {sum(s['latency_sec'] for s in stats)/len(stats):.1f}s")


if __name__ == "__main__":
    main()
