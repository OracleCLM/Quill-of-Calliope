#!/usr/bin/env python3
"""Cross-scene narrative state tracking for Calliope.AI fantasy RP assistant."""

import argparse
import json
import logging
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

import requests

log = logging.getLogger(__name__)

DEFAULT_STATE_FILE = Path(".planning/narrative_state.json")

VALID_EMOTIONS = {"neutral", "happy", "sad", "angry", "fearful", "determined", "wounded"}
VALID_STATUSES = {"alive", "wounded", "dead", "missing", "unknown"}
VALID_THREAD_STATUSES = {"active", "resolved", "abandoned"}


@dataclass
class CharState:
    name: str
    emotion: str = "neutral"
    location: str = ""
    status: str = "alive"
    last_interaction: str = ""


@dataclass
class PlotThread:
    name: str
    description: str
    status: str = "active"
    scenes_mentioned: List[str] = field(default_factory=list)
    last_updated: str = ""


@dataclass
class NarrativeState:
    chars: Dict[str, CharState] = field(default_factory=dict)
    plot_threads: List[PlotThread] = field(default_factory=list)
    current_location: str = "Kingdom of Yokai"
    current_time: str = "unknown"
    scene_count: int = 0

    # ------------------------------------------------------------------ #
    # Serialization
    # ------------------------------------------------------------------ #

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chars": {
                n: {"name": cs.name, "emotion": cs.emotion, "location": cs.location,
                    "status": cs.status, "last_interaction": cs.last_interaction}
                for n, cs in self.chars.items()
            },
            "plot_threads": [
                {"name": pt.name, "description": pt.description, "status": pt.status,
                 "scenes_mentioned": pt.scenes_mentioned, "last_updated": pt.last_updated}
                for pt in self.plot_threads
            ],
            "current_location": self.current_location,
            "current_time": self.current_time,
            "scene_count": self.scene_count,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NarrativeState":
        chars = {n: CharState(**v) for n, v in data.get("chars", {}).items()}
        threads = [PlotThread(**t) for t in data.get("plot_threads", [])]
        return cls(
            chars=chars,
            plot_threads=threads,
            current_location=data.get("current_location", "Kingdom of Yokai"),
            current_time=data.get("current_time", "unknown"),
            scene_count=data.get("scene_count", 0),
        )

    def save(self, path: Union[str, Path]) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        try:
            tmp.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
            shutil.move(str(tmp), str(path))
        except Exception:
            tmp.unlink(missing_ok=True)
            raise

    @classmethod
    def load(cls, path: Union[str, Path]) -> "NarrativeState":
        path = Path(path)
        if not path.exists():
            log.info("State file not found at %s — starting fresh", path)
            return cls()
        try:
            return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except Exception as exc:
            log.warning("Bad state file %s (%s) — starting fresh", path, exc)
            return cls()

    # ------------------------------------------------------------------ #
    # Prompt context
    # ------------------------------------------------------------------ #

    def to_prompt_context(self) -> str:
        char_parts = []
        for cs in self.chars.values():
            traits = [t for t in [cs.status, cs.emotion] if t not in ("alive", "neutral")]
            char_parts.append(f"{cs.name} ({', '.join(traits)})" if traits else cs.name)

        active = [pt.name for pt in self.plot_threads if pt.status == "active"]
        return (
            f"[Narrative State]\n"
            f"Location: {self.current_location} | Time: {self.current_time} | Scene: {self.scene_count}\n"
            f"Characters: {', '.join(char_parts) or 'none'}\n"
            f"Active plots: {', '.join(active) or 'none'}"
        )

    # ------------------------------------------------------------------ #
    # Scene update (Strategy E: cerebras via gateway)
    # ------------------------------------------------------------------ #

    def update_from_scene(
        self,
        scene_text: str,
        scene_type: str,
        scene_num: int,
        dispatch_fn=None,
        gateway_url: str = "http://localhost:8766",
    ) -> Dict[str, Any]:
        delta: Dict[str, Any] = {"chars_updated": [], "location_changed": False, "threads_updated": []}
        self.scene_count += 1

        prompt = (
            "Analyze this fantasy RP scene and return JSON only (no other text):\n"
            "{\n"
            '  "chars_seen": [{"name": str, "emotion": str, "location": str, "status": str}],\n'
            '  "location": str,\n'
            '  "time": str,\n'
            '  "plot_threads": [{"name": str, "description": str, "status": str}]\n'
            "}\n"
            f"Emotion ∈ {sorted(VALID_EMOTIONS)}. Status ∈ {sorted(VALID_STATUSES)}.\n"
            f"thread.status ∈ {sorted(VALID_THREAD_STATUSES)}.\n\n"
            f"Scene ({scene_type}, #{scene_num}):\n{scene_text[:3000]}"
        )

        try:
            if dispatch_fn is not None:
                raw = dispatch_fn(prompt)
            else:
                resp = requests.post(
                    f"{gateway_url.rstrip('/')}/llm_code",
                    json={"provider": "cerebras", "prompt": prompt},
                    timeout=30,
                )
                resp.raise_for_status()
                raw = resp.json().get("content", "")

            data = json.loads(self._extract_json(raw))
        except Exception as exc:
            log.warning("update_from_scene failed (scene %d): %s", scene_num, exc)
            return delta

        # Location
        loc = (data.get("location") or "").strip()
        if loc and loc != self.current_location:
            self.current_location = loc
            delta["location_changed"] = True

        # Time
        t = (data.get("time") or "").strip()
        if t:
            self.current_time = t

        # Characters
        for cd in data.get("chars_seen", []):
            name = (cd.get("name") or "").strip()
            if not name:
                continue
            emotion = cd.get("emotion", "neutral") if cd.get("emotion") in VALID_EMOTIONS else "neutral"
            status = cd.get("status", "alive") if cd.get("status") in VALID_STATUSES else "alive"
            loc_c = (cd.get("location") or self.current_location).strip()
            if name not in self.chars or (
                self.chars[name].emotion != emotion
                or self.chars[name].status != status
                or self.chars[name].location != loc_c
            ):
                delta["chars_updated"].append(name)
            self.chars[name] = CharState(name=name, emotion=emotion, location=loc_c,
                                         status=status, last_interaction=scene_type)

        # Plot threads
        for td in data.get("plot_threads", []):
            name = (td.get("name") or "").strip()
            if not name:
                continue
            desc = (td.get("description") or "").strip()
            st = td.get("status", "active") if td.get("status") in VALID_THREAD_STATUSES else "active"
            existing = next((p for p in self.plot_threads if p.name == name), None)
            if existing:
                if existing.description != desc or existing.status != st:
                    existing.description = desc
                    existing.status = st
                    existing.last_updated = f"scene_{scene_num}"
                    delta["threads_updated"].append(name)
                if str(scene_num) not in existing.scenes_mentioned:
                    existing.scenes_mentioned.append(str(scene_num))
            else:
                self.plot_threads.append(PlotThread(
                    name=name, description=desc, status=st,
                    scenes_mentioned=[str(scene_num)], last_updated=f"scene_{scene_num}",
                ))
                delta["threads_updated"].append(name)

        return delta

    @staticmethod
    def _extract_json(text: str) -> str:
        text = text.strip()
        # Strip markdown fences
        if "```" in text:
            parts = text.split("```")
            for i in range(1, len(parts), 2):
                block = parts[i].removeprefix("json").strip()
                try:
                    json.loads(block)
                    return block
                except Exception:
                    pass
        # Brace scanning
        start = text.find("{")
        if start != -1:
            depth = 0
            for j, ch in enumerate(text[start:], start):
                depth += (ch == "{") - (ch == "}")
                if depth == 0:
                    candidate = text[start : j + 1]
                    try:
                        json.loads(candidate)
                        return candidate
                    except Exception:
                        break
        # Last resort: whole text
        return text


def main() -> None:
    parser = argparse.ArgumentParser(description="Narrative state manager")
    parser.add_argument("--state-file", default=str(DEFAULT_STATE_FILE))
    grp = parser.add_mutually_exclusive_group(required=True)
    grp.add_argument("--show", action="store_true")
    grp.add_argument("--reset", action="store_true")
    args = parser.parse_args()

    sf = Path(args.state_file)
    if args.reset:
        NarrativeState().save(sf)
        print("State reset.")
    else:
        print(NarrativeState.load(sf).to_prompt_context())


if __name__ == "__main__":
    main()
