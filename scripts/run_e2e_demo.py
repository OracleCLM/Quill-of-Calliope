#!/usr/bin/env python3
"""Calliope.AI Phase-3 E2E demo — 3-scene chain + TTS + WS broadcast cycle."""
from __future__ import annotations
import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

import requests
from tqdm import tqdm

sys.path.insert(0, str(Path(__file__).parent))
from scene_narrative import generate_scene_chain  # noqa: E402
from tts_phoneme_export import export_phonemes  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    encoding="utf-8",
    stream=sys.stdout,
)
log = logging.getLogger("e2e_demo")

LLM_GW = "http://localhost:8766"
WS_SRV = "http://localhost:8767"
SCENE_STATE_MAP = {
    "action_combat": "talking",
    "lore_exposition": "talking",
    "romantic_fade_to_black": "listening",
    "character_death": "talking",
    "ooc_meta": "idle",
}


def _healthy(url: str, timeout: int = 3) -> bool:
    try:
        with urllib.request.urlopen(f"{url}/health", timeout=timeout):
            return True
    except Exception:
        return False


def _start_daemon(script: str, port: int, label: str) -> subprocess.Popen | None:
    if _healthy(f"http://localhost:{port}"):
        log.info("%s already running on %d", label, port)
        return None
    log.info("Starting %s on port %d...", label, port)
    proc = subprocess.Popen(
        [sys.executable, str(Path(__file__).parent / script)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    for _ in range(6):
        time.sleep(0.5)
        if _healthy(f"http://localhost:{port}"):
            log.info("%s ready (PID %d)", label, proc.pid)
            return proc
    log.warning("%s did not respond in time — continuing without", label)
    return proc


def _post(endpoint: str, data: dict) -> bool:
    try:
        r = requests.post(f"{WS_SRV}{endpoint}", json=data, timeout=3)
        return r.status_code == 200
    except Exception as exc:
        log.warning("POST %s failed: %s", endpoint, exc)
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Calliope.AI Phase-3 E2E demo")
    parser.add_argument("--output-dir", default="scenes/m3_e2e_demo/")
    parser.add_argument("--no-start-daemons", action="store_true")
    parser.add_argument("--skip-tts", action="store_true")
    parser.add_argument("--gateway-url", default=LLM_GW)
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    log_events: list[str] = []

    def log_event(kind: str, detail: str) -> None:
        entry = f"{datetime.now().isoformat(timespec='seconds')} | {kind} | {detail}"
        log_events.append(entry)
        log.info("[event] %s | %s", kind, detail)

    # ── 1. Daemon startup ────────────────────────────────────────────────────
    procs: list[subprocess.Popen] = []
    if not args.no_start_daemons:
        p = _start_daemon("llm_gateway_http.py", 8766, "llm-gateway")
        if p:
            procs.append(p)
        p = _start_daemon("mascot_ws_server.py", 8767, "mascot-ws")
        if p:
            procs.append(p)

    ws_up = _healthy(WS_SRV)
    gw_up = _healthy(args.gateway_url)
    log.info("Services — LLM gateway: %s | WS server: %s", "UP" if gw_up else "DOWN", "UP" if ws_up else "DOWN")
    if not gw_up:
        log.error("LLM gateway unavailable — aborting scene generation")
        sys.exit(1)

    # ── 2. Scene generation ──────────────────────────────────────────────────
    chain_args = argparse.Namespace(
        seed="Aurora confronts the demon at the city gates",
        n_scenes=3,
        scene_types="action_combat,lore_exposition,romantic_fade_to_black",
        char_list="Aurora,Grimm,Narrator",
        location="Kingdom of Yokai",
        output_dir=str(out),
        nsfw_score=json.dumps({"nudity_explicit": 0, "violence_gore": 1, "non_consent": 0, "minors_adjacent": 0}),
        gateway_url=args.gateway_url,
        config="data/llm_routing_config.yaml",
        state_file=None,
    )
    nsfw = {"nudity_explicit": 0, "violence_gore": 1, "non_consent": 0, "minors_adjacent": 0}
    try:
        from route_scene import DEFAULT_CONFIG
        cfg = DEFAULT_CONFIG
    except Exception:
        cfg = {}

    log.info("Generating 3-scene chain...")
    try:
        stats = generate_scene_chain(chain_args, cfg, nsfw)
    except Exception as exc:
        log.error("Scene generation failed: %s — using placeholders", exc)
        stats = [{"scene_type": t, "status": "placeholder", "scene_text": "The story continues..."}
                 for t in ["action_combat", "lore_exposition", "romantic_fade_to_black"]]

    # ── 3. Per-scene TTS + WS broadcast ─────────────────────────────────────
    tts_count = ws_count = 0
    for i, scene in enumerate(tqdm(stats, desc="Broadcasting scenes"), 1):
        scene_type = scene.get("scene_type", "default")
        state = SCENE_STATE_MAP.get(scene_type, "talking")

        if ws_up and _post("/event/state", {"state": state}):
            log_event("state", f"scene_{i} → {state}")
            ws_count += 1

        if not args.skip_tts and ws_up:
            excerpt = scene.get("scene_text", "")[:200] or "Scene excerpt unavailable."
            try:
                phonemes = export_phonemes(excerpt, str(out))["phonemes"]
                if _post("/event/tts", {"type": "start", "data": {"scene_idx": i, "phoneme_count": len(phonemes)}}):
                    log_event("tts_start", f"scene_{i}")
                    tts_count += 1
                time.sleep(0.5)
                if _post("/event/tts", {"type": "end", "data": {"scene_idx": i}}):
                    log_event("tts_end", f"scene_{i}")
                    tts_count += 1
            except Exception as exc:
                log.warning("TTS export failed scene %d: %s", i, exc)

    # ── 4. Write log + summary ───────────────────────────────────────────────
    (out / "demo_log.txt").write_text("\n".join(log_events), encoding="utf-8")
    log.info("DONE — %d scenes | %d TTS events | %d WS broadcasts | log: %s/demo_log.txt",
             len(stats), tts_count, ws_count, out)

    for p in procs:
        p.terminate()


if __name__ == "__main__":
    main()
