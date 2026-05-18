#!/usr/bin/env python3
"""LLM scene routing decision engine for Quill of Calliope RP assistant.

Implements docs/llm_routing.md v1 operator-approved matrix.
Handles content safety blocks, NSFW threshold forcing, and scene-type→tier mapping.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import urllib.request
from typing import Dict, Optional

import yaml

DEFAULT_CONFIG: Dict = {
    "matrix": {
        "action_combat":          {"tier": "cerebras_workhorse",   "provider": "cerebras",    "model": "qwen-3-235b-a22b"},
        "character_death":        {"tier": "cerebras_workhorse",   "provider": "cerebras",    "model": "qwen-3-235b-a22b"},
        "nsfw_explicit":          {"tier": "ollama_uncensored",    "provider": "ollama",      "model": "dolphin-mistral-24b"},
        "romantic_fade_to_black": {"tier": "groq_fast",            "provider": "groq",        "model": "llama-3.3-70b-versatile"},
        "ooc_meta":               {"tier": "groq_fast",            "provider": "groq",        "model": "llama-3.3-70b-versatile"},
        "system_command":         {"tier": "groq_fast",            "provider": "groq",        "model": "llama-3.3-70b-versatile"},
        "lore_exposition":        {"tier": "openrouter_reasoning", "provider": "openrouter",  "model": "deepseek-r1-0528"},
        "climax_rare":            {"tier": "claude_subprocess",    "provider": "claude",      "model": "claude-opus-4-7"},
        "default":                {"tier": "cerebras_workhorse",   "provider": "cerebras",    "model": "qwen-3-235b-a22b"},
    },
    "nsfw_threshold": 2,
    "block_thresholds": {
        "non_consent": 3,
        "minors_adjacent": 3,
    },
}


class BlockedContentError(Exception):
    """Raised when content scores exceed block thresholds."""

    def __init__(self, message: str, dimension: str, score: int) -> None:
        super().__init__(message)
        self.dimension = dimension
        self.score = score


def load_config(path: str) -> Dict:
    """Load and validate routing config from YAML. Raises ValueError on bad schema."""
    with open(path, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    for key in ("matrix", "nsfw_threshold", "block_thresholds"):
        if key not in config:
            raise ValueError(f"Missing required config key: {key!r}")
    for key in ("non_consent", "minors_adjacent"):
        if key not in config["block_thresholds"]:
            raise ValueError(f"Missing block_threshold: {key!r}")
    if "default" not in config["matrix"]:
        raise ValueError("matrix must include a 'default' entry")
    return config


def route_scene(
    scene_type: str,
    nsfw_score: Dict[str, int],
    char_relevance: str = "low",
    config: Optional[Dict] = None,
) -> Dict:
    """Decide which LLM tier to use for a scene.

    Priority order:
      1. Block check (non_consent/minors_adjacent >= threshold → raise)
      2. Ollama force (any dim >= nsfw_threshold → local)
      3. Scene-type matrix lookup
      4. Char-relevance LoRA candidate annotation
    """
    if config is None:
        config = DEFAULT_CONFIG

    if char_relevance not in ("low", "high"):
        raise ValueError("char_relevance must be 'low' or 'high'")

    # 1 — Hard block
    nc = nsfw_score.get("non_consent", 0)
    ma = nsfw_score.get("minors_adjacent", 0)
    if nc >= config["block_thresholds"]["non_consent"]:
        raise BlockedContentError(
            f"Blocked: non_consent score {nc} >= {config['block_thresholds']['non_consent']}",
            "non_consent", nc,
        )
    if ma >= config["block_thresholds"]["minors_adjacent"]:
        raise BlockedContentError(
            f"Blocked: minors_adjacent score {ma} >= {config['block_thresholds']['minors_adjacent']}",
            "minors_adjacent", ma,
        )

    max_nsfw = max(nsfw_score.values()) if nsfw_score else 0

    # 2 — Force Ollama if any dim >= threshold
    if max_nsfw >= config["nsfw_threshold"]:
        entry = config["matrix"].get("nsfw_explicit", config["matrix"]["default"])
        result = {
            "tier": entry["tier"],
            "provider": entry["provider"],
            "model": entry["model"],
            "rationale": (
                f"scene_type={scene_type} nsfw_max={max_nsfw} "
                f"char_relevance={char_relevance} → {entry['tier']} [nsfw-forced]"
            ),
        }
        if char_relevance == "high":
            result["lora_candidate"] = True
        return result

    # 3 — Scene-type matrix
    entry = config["matrix"].get(scene_type, config["matrix"]["default"])
    result = {
        "tier": entry["tier"],
        "provider": entry["provider"],
        "model": entry["model"],
        "rationale": (
            f"scene_type={scene_type} nsfw_max={max_nsfw} "
            f"char_relevance={char_relevance} → {entry['tier']}"
        ),
    }

    # 4 — Char relevance annotation (LoRA path: M4+)
    if char_relevance == "high":
        result["lora_candidate"] = True

    return result


def dispatch_to_tier(
    tier_name: str,
    prompt: str,
    config: Optional[Dict] = None,
    gateway_url: str = "http://localhost:8765",
    ollama_url: str = "http://localhost:11434",
    timeout: int = 30,
    max_retries: int = 3,
) -> str:
    if config is None:
        config = DEFAULT_CONFIG
    entry = next(
        (e for e in config["matrix"].values() if e["tier"] == tier_name),
        config["matrix"]["default"],
    )
    provider, model = entry["provider"], entry["model"]
    logging.info("[dispatch] tier=%s provider=%s model=%s", tier_name, provider, model)

    # Tier routing
    if provider in ("cerebras", "groq", "openrouter"):
        tool = "llm_ask" if provider == "groq" else "llm_code"
        return _call_gateway(gateway_url, tool, provider, prompt, timeout, max_retries)
    elif provider == "ollama":
        # Fallback model: qwen2.5:7b-instruct if dolphin unavailable
        for m in (model, "qwen2.5:7b-instruct", "phi3:mini"):
            try:
                return _call_ollama(ollama_url, m, prompt, timeout)
            except Exception as exc:
                logging.warning("[dispatch] ollama model %s failed: %s", m, exc)
        raise RuntimeError("All ollama models failed")
    elif provider == "claude":
        return _call_claude_subprocess(prompt, model, timeout)
    else:
        raise ValueError(f"Unknown provider: {provider!r}")


def _call_gateway(url: str, tool: str, provider: str, prompt: str, timeout: int, max_retries: int) -> str:
    """Call local HTTP wrapper for llm-gateway (localhost:8766)."""
    import json as _json
    endpoint = "llm_ask" if tool == "llm_ask" else "llm_code"
    # url param ignored (deprecated direct API), always use localhost:8766
    gateway_base = os.environ.get("CALLIOPE_LLM_GATEWAY", "http://localhost:8766")
    payload = _json.dumps({"provider": provider, "prompt": prompt}).encode()
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                f"{gateway_base}/{endpoint}",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = _json.loads(resp.read())
                content = data.get("content", "")
                if content:
                    logging.info("[gateway] %s/%s → %d chars", provider, endpoint, len(content))
                    return content
                raise ValueError("Empty content from gateway")
        except Exception as exc:
            wait = 2 ** attempt
            logging.warning("[gateway/%s] attempt %d/%d failed (%s) — retry in %ds",
                            provider, attempt + 1, max_retries, exc, wait)
            if attempt < max_retries - 1:
                time.sleep(wait)
    raise RuntimeError(f"Gateway call to {provider} failed after {max_retries} attempts")


def _call_ollama(url: str, model: str, prompt: str, timeout: int) -> str:
    import json as _json
    payload = _json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = _json.loads(resp.read())
        return data.get("response", "")


def _call_claude_subprocess(prompt: str, model: str, timeout: int) -> str:
    result = subprocess.run(
        ["claude", "--model", model, "--print"],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude subprocess failed: {result.stderr[:200]}")
    return result.stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser(description="Calliope scene routing engine")
    parser.add_argument("--scene-type", default="action_combat")
    parser.add_argument(
        "--nsfw-score",
        default='{"nudity_explicit":0,"violence_gore":0,"non_consent":0,"minors_adjacent":0}',
    )
    parser.add_argument("--char-relevance", choices=["low", "high"], default="low")
    parser.add_argument("--config", default="data/llm_routing_config.yaml")
    parser.add_argument(
        "--speak", action="store_true",
        help="[STUB] Read routing rationale aloud via TTS (M3 demo, real scene-gen in future sprint)",
    )
    args = parser.parse_args()

    try:
        config = load_config(args.config)
    except Exception as e:
        logging.warning("Config load failed (%s) — using DEFAULT_CONFIG", e)
        config = DEFAULT_CONFIG

    try:
        nsfw_score = json.loads(args.nsfw_score)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON for --nsfw-score: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = route_scene(args.scene_type, nsfw_score, args.char_relevance, config)
        print(json.dumps(result, indent=2))
        if args.speak:
            # STUB: real scene text not available yet (scene-gen sprint pending)
            speak_text = f"Would speak: {result['rationale']}"
            print(f"[--speak stub] {speak_text}", file=sys.stderr)
    except BlockedContentError as e:
        print(f"BLOCKED: {e}", file=sys.stderr)
        sys.exit(2)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
