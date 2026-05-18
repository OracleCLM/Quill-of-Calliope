#!/usr/bin/env python3
"""Narrative continuity tester — chains 5 scenes, checks char + location + temporal consistency."""

import argparse
import logging
import sys
import time
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from route_scene import dispatch_to_tier, load_config  # noqa: E402

log = logging.getLogger(__name__)


CHAIN_TYPES = [
    "action_combat",
    "action_aftermath",
    "intimate_dialogue",
    "mystery_investigation",
    "transition_temporal",
]

CHAIN_SEED = "Aurora and Filomena investigate a series of disappearances in the capital market district of the Kingdom of Yokai."
CHAIN_CHARS = ["Aurora", "Filomena", "Koibo"]
CHAIN_LOCATION = "Kingdom of Yokai capital"


def _extract_names(text: str, candidates: list) -> set:
    """Return set of candidate names mentioned in text."""
    return {n for n in candidates if n.lower() in text.lower()}


def _has_location_ref(text: str, location_words: list) -> bool:
    return any(w.lower() in text.lower() for w in location_words)


def _has_temporal_conflict(texts: list) -> bool:
    """Simple heuristic: if scene N mentions 'dawn' and scene N+1 mentions 'dusk', flag."""
    day_markers = ["dawn", "morning", "midday", "noon", "afternoon"]
    night_markers = ["dusk", "evening", "night", "midnight"]
    flags = []
    for t in texts:
        tl = t.lower()
        if any(m in tl for m in day_markers):
            flags.append("day")
        elif any(m in tl for m in night_markers):
            flags.append("night")
        else:
            flags.append("?")
    # Detect immediate flip: day→night→day or night→day→night
    for i in range(len(flags) - 1):
        if flags[i] != "?" and flags[i + 1] != "?" and flags[i] != flags[i + 1]:
            if i + 2 < len(flags) and flags[i + 2] == flags[i]:
                return True
    return False


def run_chain(config, gateway_url, char_list, location, seed, chain_types, dry_run=False) -> dict:
    """Run a 5-scene chain. Returns analysis dict."""
    scenes = []
    prev_text = ""
    location_words = location.split()

    for i, stype in enumerate(chain_types, 1):
        tier = config["matrix"].get(stype, config["matrix"]["default"])["tier"]
        if i == 1:
            prompt = (
                f"Scene 1 — {stype.replace('_', ' ')}.\n"
                f"Location: {location}\nCharacters: {', '.join(char_list)}\n\n{seed}\n\n"
                f"Write 2-3 paragraphs, third-person fantasy RP prose, 150-200 words."
            )
        else:
            prev_snippet = prev_text[-300:] if prev_text else ""
            prompt = (
                f"Scene {i} — {stype.replace('_', ' ')}. Continue the narrative.\n"
                f"Location: {location}\nCharacters: {', '.join(char_list)}\n\n"
                f"Previous scene ending:\n{prev_snippet}\n\n"
                f"Continue in 2-3 paragraphs, third-person, 150-200 words."
            )

        log.info("Chain scene %d/%d [%s] → %s", i, len(chain_types), stype, tier)
        t0 = time.time()
        if dry_run:
            text = f"[DRY RUN scene {i}: {stype}] Aurora and Filomena moved through the capital district."
        else:
            try:
                text = dispatch_to_tier(tier, prompt, config=config, gateway_url=gateway_url, timeout=45, max_retries=2)
                text = text.strip()
            except Exception as exc:
                log.warning("Scene %d failed: %s", i, exc)
                text = f"[FAILED: {exc}]"

        scenes.append({"scene_num": i, "type": stype, "tier": tier,
                       "text": text, "latency": round(time.time() - t0, 2)})
        prev_text = text

    # Continuity analysis
    texts = [s["text"] for s in scenes]
    chars_per_scene = [_extract_names(t, char_list) for t in texts]
    location_hits = [_has_location_ref(t, location_words) for t in texts]
    temporal_conflict = _has_temporal_conflict(texts)

    # Char continuity: chars in scene N+1 overlap with scene N
    continuity_scores = []
    for i in range(len(chars_per_scene) - 1):
        a, b = chars_per_scene[i], chars_per_scene[i + 1]
        overlap = len(a & b)
        continuity_scores.append(overlap)

    analysis = {
        "chain_length": len(scenes),
        "chars_mentioned": [list(c) for c in chars_per_scene],
        "location_refs": location_hits,
        "temporal_conflict_detected": temporal_conflict,
        "char_continuity_scores": continuity_scores,
        "avg_char_continuity": (sum(continuity_scores) / len(continuity_scores)) if continuity_scores else 0,
        "scenes": [{"scene_num": s["scene_num"], "type": s["type"], "latency": s["latency"],
                    "chars": len(s["text"])} for s in scenes],
    }
    return analysis, scenes


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrative continuity tester — 5-scene chain")
    parser.add_argument("--gateway-url", default="http://localhost:8766")
    parser.add_argument("--config", type=Path, default="data/llm_routing_config.yaml")
    parser.add_argument("--output", type=Path, default=".planning/CONTINUITY_REPORT.md")
    parser.add_argument("--char-list", default="Aurora,Filomena,Koibo")
    parser.add_argument("--location", default="Kingdom of Yokai capital")
    parser.add_argument("--seed", default=CHAIN_SEED)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    config = load_config(str(args.config))
    char_list = [c.strip() for c in args.char_list.split(",")]

    log.info("Running 5-scene continuity chain...")
    analysis, scenes = run_chain(
        config, args.gateway_url, char_list, args.location, args.seed,
        CHAIN_TYPES, dry_run=args.dry_run,
    )

    # Write markdown report
    args.output.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Narrative Continuity Report\n",
        f"**Generated**: {__import__('datetime').datetime.utcnow().isoformat()}Z  ",
        f"**Chain length**: {analysis['chain_length']} scenes  ",
        f"**Location**: {args.location}  ",
        f"**Characters**: {', '.join(char_list)}\n",
        "## Scene chain\n",
        "| # | Type | Tier | Chars | Latency |",
        "|---|------|------|-------|---------|",
    ]
    for s in analysis["scenes"]:
        lines.append(f"| {s['scene_num']} | {s['type']} | — | {s['chars']} | {s['latency']}s |")

    lines += [
        "\n## Continuity analysis\n",
        f"- **Char continuity scores** (overlap scene N→N+1): {analysis['char_continuity_scores']}",
        f"- **Avg char continuity**: {analysis['avg_char_continuity']:.2f} chars shared per transition",
        f"- **Location refs per scene**: {analysis['location_refs']}",
        f"- **Temporal conflict detected**: {analysis['temporal_conflict_detected']}",
        "\n## Chars mentioned per scene\n",
    ]
    for i, chars in enumerate(analysis["chars_mentioned"], 1):
        lines.append(f"- Scene {i}: {', '.join(chars) if chars else '(none detected)'}")

    lines += ["\n## Scene texts\n"]
    for s in scenes:
        lines.append(f"### Scene {s['scene_num']} — {s['type']}\n\n{s['text']}\n")

    args.output.write_text("\n".join(lines), encoding="utf-8")

    # Console summary
    print(f"\n{'='*50}")
    print(f"Continuity chain: {analysis['chain_length']} scenes")
    print(f"Avg char continuity: {analysis['avg_char_continuity']:.2f}")
    print(f"Temporal conflict: {analysis['temporal_conflict_detected']}")
    print(f"Report → {args.output}")


if __name__ == "__main__":
    main()
