#!/usr/bin/env python3
"""
Quill of Calliope M3 — narrative chain generator.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).parent))

from route_scene import (  # noqa: E402
    DEFAULT_CONFIG,
    dispatch_to_tier,
    load_config,
    route_scene,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def build_scene_prompt(
    i: int,
    seed: str,
    location: str,
    char_list_str: str,
    prev_scene_text: str,
    state_context: str = "",
) -> str:
    """Build the prompt for scene i, optionally injecting narrative state context."""
    state_block = f"\n{state_context}\n" if state_context else ""
    if i == 1:
        prompt = f"[Location: {location}] [Characters: {char_list_str}]{state_block}\n\nScene 1:\n{seed}"
    else:
        prev_excerpt = prev_scene_text[:200]
        paragraphs = [p.strip() for p in prev_scene_text.split("\n\n") if p.strip()]
        last_paragraph = paragraphs[-1] if paragraphs else ""
        prompt = (
            f"[Continuation of previous scene]{state_block}\n"
            f"[Previous scene excerpt]:\n{prev_excerpt}\n\n"
            f"Scene {i} (continue the narrative):\n{last_paragraph}"
        )
    prompt += "\n\nWrite 2-3 paragraphs in third person, fantasy RP style."
    return prompt


def generate_scene_chain(
    args: argparse.Namespace,
    config: Dict,
    nsfw_score: Dict[str, float],
) -> List[Dict[str, Any]]:
    """Generate a chain of scenes and return list of stats."""
    scenes: List[str] = []
    stats: List[Dict[str, Any]] = []
    scene_types_list = args.scene_types.split(",")
    timestamp = datetime.now().isoformat(timespec="seconds")
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Narrative state integration (Task B)
    state_file = getattr(args, "state_file", None)
    narrative_state = None
    if state_file:
        from narrative_state import NarrativeState  # noqa: PLC0415
        narrative_state = NarrativeState.load(state_file)
        logger.info("Loaded narrative state: scene_count=%d chars=%d",
                    narrative_state.scene_count, len(narrative_state.chars))

    for i in range(1, args.n_scenes + 1):
        scene_type = scene_types_list[(i - 1) % len(scene_types_list)]
        state_context = narrative_state.to_prompt_context() if narrative_state else ""
        prompt = build_scene_prompt(
            i=i,
            seed=args.seed,
            location=args.location,
            char_list_str=args.char_list or "—",
            prev_scene_text=scenes[-1] if scenes else "",
            state_context=state_context,
        )

        try:
            routing = route_scene(
                scene_type=scene_type,
                nsfw_score=nsfw_score,
                config=config,
            )
            tier = routing["tier"]
            provider = routing["provider"]
            t0 = time.time()
            scene_text = dispatch_to_tier(
                tier_name=tier,
                prompt=prompt,
                config=config,
                gateway_url=args.gateway_url,
                timeout=30,
            )
            latency_ms = int((time.time() - t0) * 1000)
            status = "ok"
        except Exception as e:
            logger.error("Scene %d generation failed: %s", i, e)
            scene_text = f"[Scene {i} generation failed]"
            tier = "unknown"
            provider = "unknown"
            latency_ms = 0
            status = "failed"

        # Save scene file
        safe_scene_type = scene_type.replace("/", "_")
        scene_filename = output_dir / f"scene_{i:02d}_{safe_scene_type}.md"
        with open(scene_filename, "w", encoding="utf-8") as f:
            f.write(
                f"# Scene {i}: {scene_type}\n"
                f"**Tier**: {tier} | **Provider**: {provider} | "
                f"**Latency**: {latency_ms}ms | **Chars**: {len(scene_text)}\n\n"
                f"{scene_text}\n\n"
                f"---\n"
                f"_Quill of Calliope M3 narrative chain — {timestamp}_\n"
            )

        stats.append(
            {
                "scene_num": i,
                "scene_type": scene_type,
                "tier": tier,
                "provider": provider,
                "latency_ms": latency_ms,
                "chars": len(scene_text),
                "status": status,
            }
        )
        scenes.append(scene_text)

        # Update + persist narrative state (Task B)
        if narrative_state and status == "ok":
            delta = narrative_state.update_from_scene(
                scene_text=scene_text,
                scene_type=scene_type,
                scene_num=i,
                gateway_url=getattr(args, "gateway_url", "http://localhost:8766"),
            )
            narrative_state.save(state_file)
            logger.info("State delta — chars:%s loc_changed:%s threads:%s",
                        delta["chars_updated"], delta["location_changed"], delta["threads_updated"])

    return stats


def write_narrative_index(
    output_dir: Path,
    stats: List[Dict[str, Any]],
    seed: str,
    location: str,
    char_list_str: str,
    timestamp: str,
) -> None:
    """Write the narrative index markdown file."""
    index_path = output_dir / "narrative_index.md"
    sum_latency = sum(s["latency_ms"] for s in stats)
    avg_latency = int(sum_latency / len(stats)) if stats else 0

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(f"# Narrative Index — {timestamp}\n")
        f.write(f"**Seed**: {seed}\n")
        f.write(f"**Location**: {location}\n")
        f.write(f"**Characters**: {char_list_str or '—'}\n\n")

        f.write("## Scene Summary\n")
        f.write("| # | Type | Tier | Latency | Chars | Status |\n")
        f.write("|---|------|------|---------|-------|--------|\n")
        for s in stats:
            f.write(
                f"| {s['scene_num']} | {s['scene_type']} | {s['tier']} | "
                f"{s['latency_ms']}ms | {s['chars']} | {s['status']} |\n"
            )

        f.write("\n## Timeline\n")
        f.write(" → ".join(f"Scene {s['scene_num']}" for s in stats))
        f.write("\n\n")
        f.write(f"---\nTotal latency: {sum_latency}ms | Avg: {avg_latency}ms\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Quill of Calliope M3 narrative chain generator")
    parser.add_argument("--seed", type=str, required=True, help="Starting prompt for scene 1")
    parser.add_argument("--n-scenes", type=int, default=3, help="Number of scenes in chain")
    parser.add_argument(
        "--scene-types",
        type=str,
        default="action_combat,lore_exposition,romantic_fade_to_black",
        help="Comma-separated list of scene types",
    )
    parser.add_argument(
        "--char-list",
        type=str,
        default="",
        help="Comma-separated list of characters",
    )
    parser.add_argument(
        "--location",
        type=str,
        default="Kingdom of Yokai",
        help="Setting location",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default="scenes/m3_narratives/",
        help="Output directory for scene files",
    )
    parser.add_argument(
        "--nsfw-score",
        type=str,
        default='{"nudity_explicit":0,"violence_gore":0,"non_consent":0,"minors_adjacent":0}',
        help="JSON string of NSFW scores",
    )
    parser.add_argument(
        "--gateway-url",
        type=str,
        default="http://localhost:8766",
        help="Gateway URL for dispatch",
    )
    parser.add_argument(
        "--config",
        type=str,
        default="data/llm_routing_config.yaml",
        help="Path to routing config YAML",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        default=None,
        help="Path to narrative state JSON (enables cross-scene state tracking)",
    )

    args = parser.parse_args()

    # Parse nsfw_score JSON
    try:
        nsfw_score = json.loads(args.nsfw_score)
    except json.JSONDecodeError as e:
        print(f"Error parsing --nsfw-score JSON: {e}", file=sys.stderr)
        sys.exit(1)

    # Load config
    try:
        config = load_config(args.config)
    except (ValueError, FileNotFoundError) as e:
        logger.warning("Failed to load config from %s: %s. Using default.", args.config, e)
        config = DEFAULT_CONFIG

    # Run generation
    stats = generate_scene_chain(args, config, nsfw_score)

    # Write index
    timestamp = datetime.now().isoformat(timespec="seconds")
    write_narrative_index(
        output_dir=Path(args.output_dir),
        stats=stats,
        seed=args.seed,
        location=args.location,
        char_list_str=args.char_list or "—",
        timestamp=timestamp,
    )

    # Print stats to stdout
    for stat in stats:
        print(stat)


if __name__ == "__main__":
    main()
