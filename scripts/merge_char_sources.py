#!/usr/bin/env python3
import argparse
import json
import sys
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests
import yaml


def slugify(name: str) -> str:
    import re
    s = name.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s_]+", "-", s)
    return s.strip("-")


def _prefix_word_match(name: str, candidates: List[str]) -> Optional[str]:
    """Return the first candidate that is a word-prefix of name or vice versa.

    Handles cases like 'Aurora of Winter' vs 'Aurora' (one starts the other
    at a word boundary), which SequenceMatcher.ratio() misses at threshold 0.7.
    """
    name_l = name.lower().strip()
    for c in candidates:
        c_l = c.lower().strip()
        if not c_l:
            continue
        # name starts with candidate (e.g. name="Aurora of Winter", c="Aurora")
        if name_l.startswith(c_l) and (
            len(name_l) == len(c_l) or name_l[len(c_l)] in (" ", "-", "'", "\"")
        ):
            return c
        # candidate starts with name (e.g. name="Aurora", c="Aurora of Winter")
        if c_l.startswith(name_l) and (
            len(c_l) == len(name_l) or c_l[len(name_l)] in (" ", "-", "'", "\"")
        ):
            return c
    return None


def fuzzy_match_chars(
    name: str,
    candidates: List[str],
    threshold: float = 0.7,
    alias_map: Optional[Dict[str, str]] = None,
) -> Optional[str]:
    name_l = name.lower().strip()
    # 1. Explicit alias override (operator-provided)
    if alias_map:
        hit = alias_map.get(name_l)
        if hit:
            # return exact candidate string if present, otherwise the alias value
            for c in candidates:
                if c.lower().strip() == hit.lower().strip():
                    return c
            return hit
    # 2. Prefix-word match (zero-config, handles long Tupperbox names)
    prefix_hit = _prefix_word_match(name, candidates)
    if prefix_hit is not None:
        return prefix_hit
    # 3. SequenceMatcher ratio fallback
    best, best_ratio = None, threshold
    for c in candidates:
        r = SequenceMatcher(None, name_l, c.lower()).ratio()
        if r > best_ratio:
            best_ratio = r
            best = c
    return best


def load_tuppers(path: str) -> List[Dict]:
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("tuppers", [])


def load_discord_sheets(path: str) -> List[Dict]:
    sheets = []
    if not Path(path).exists():
        return sheets
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                sheets.append(json.loads(line))
    return sheets


def load_corpus_samples(path: str, max_per_char: int = 50) -> Dict[str, Dict]:
    """Returns {char_name: {"messages": [...], "last_ts": "ISO8601"}}."""
    raw: Dict[str, List[Tuple[str, str]]] = {}
    if not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            char = rec.get("character")
            msg = (rec.get("message") or "").strip()
            ts = rec.get("timestamp", "")
            if not char or not msg:
                continue
            raw.setdefault(char, []).append((ts, msg))

    result = {}
    for char, pairs in raw.items():
        pairs.sort(key=lambda x: x[0], reverse=True)
        latest_ts = pairs[0][0] if pairs else ""
        messages = [m for _, m in pairs[:max_per_char]]
        result[char] = {"messages": messages, "last_ts": latest_ts}
    return result


def _parse_dt(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


def llm_intelligent_merge(
    tupper_desc: str,
    sheet_text: str,
    llm_gateway_url: str = "http://localhost:8765",
) -> str:
    """Cerebras intelligent merge — fallback to longest text on error."""
    task = (
        "Merge these two character descriptions into one coherent, comprehensive description. "
        "Preserve all unique details from both. Avoid redundancy. "
        "Return only the merged text.\n\n"
        f"Description 1 (Tupperbox):\n{tupper_desc}\n\n"
        f"Description 2 (Discord Sheet excerpt):\n{sheet_text[:2000]}"
    )
    try:
        resp = requests.post(
            f"{llm_gateway_url.rstrip('/')}/call",
            json={"tool": "llm_code", "args": {"task": task, "provider": "cerebras"}},
            timeout=30,
        )
        if resp.status_code == 200:
            content = resp.json().get("content", "").strip()
            return content or max(tupper_desc, sheet_text, key=len)
    except Exception:
        pass
    return max(tupper_desc, sheet_text, key=len)


def merge_char(
    tupper: Optional[Dict],
    sheet: Optional[Dict],
    samples: Dict,
    llm_merge_fn=None,
    llm_gateway_url: str = "http://localhost:8765",
) -> Dict:
    if not tupper and not sheet:
        raise ValueError("At least one of tupper or sheet must be provided")

    name = (tupper or sheet)["name"] if tupper else sheet["char_name"]  # type: ignore[index]
    slug = slugify(name)
    author_id = str((sheet or {}).get("author_id") or (tupper or {}).get("author_id") or "")

    tupper_desc = (tupper.get("description") or "").strip() if tupper else ""
    sheet_text = (sheet.get("sheet_text") or "").strip() if sheet else ""
    thread_id = sheet.get("thread_id") if sheet else None

    tupper_dt = _parse_dt((tupper or {}).get("last_used") or (tupper or {}).get("created_at"))
    sheet_dt = _parse_dt((sheet or {}).get("last_updated") or (sheet or {}).get("created_at"))

    # --- physical ---
    physical = ""
    physical_source = ""
    physical_last_updated: Optional[str] = None
    deprecated_physical_v1: Optional[str] = None

    if tupper and not sheet:
        physical = tupper_desc
        physical_source = "tupperbox"
        physical_last_updated = (tupper.get("last_used") or tupper.get("created_at"))
    elif sheet and not tupper:
        physical = sheet_text[:500]
        physical_source = "discord-thread"
        physical_last_updated = (sheet.get("last_updated") or sheet.get("created_at"))
    elif tupper and sheet and tupper_dt and sheet_dt:
        gap_days = abs((sheet_dt - tupper_dt).days)
        if sheet_dt > tupper_dt and gap_days > 180:
            physical = sheet_text[:500]
            physical_source = "discord-thread"
            physical_last_updated = (sheet.get("last_updated") or sheet.get("created_at"))
            deprecated_physical_v1 = tupper_desc
        elif tupper_dt >= sheet_dt and gap_days > 180:
            physical = tupper_desc
            physical_source = "tupperbox"
            physical_last_updated = (tupper.get("last_used") or tupper.get("created_at"))
            deprecated_physical_v1 = sheet_text[:500]
        else:
            # Close in recency: intelligent merge if llm available
            if llm_merge_fn and tupper_desc and sheet_text:
                try:
                    physical = llm_merge_fn(tupper_desc, sheet_text, llm_gateway_url)
                except Exception:
                    physical = tupper_desc
            else:
                physical = tupper_desc if tupper_desc else sheet_text[:500]
            physical_source = "merged"
            physical_last_updated = (tupper.get("last_used") or tupper.get("created_at"))
    elif tupper and sheet:
        # One or both dates missing — use tupper as fallback
        physical = tupper_desc or sheet_text[:500]
        physical_source = "tupperbox" if tupper_desc else "discord-thread"
        physical_last_updated = (tupper.get("last_used") or tupper.get("created_at"))

    # --- lore ---
    lore = sheet_text if sheet else tupper_desc
    lore_source = "discord-thread" if sheet else "tupperbox"
    lore_last_updated = (
        (sheet.get("last_updated") or sheet.get("created_at")) if sheet
        else (tupper.get("last_used") or tupper.get("created_at") if tupper else None)
    )

    # --- voice ---
    voice_msgs = samples.get("messages", []) if samples else []
    voice_last_ts = samples.get("last_ts") if samples else None
    voice_last_day = voice_last_ts[:10] if voice_last_ts else None

    # Build output
    meta: Dict = {
        "physical": {
            "last_updated": physical_last_updated,
            "source": physical_source,
        },
        "lore": {
            "last_updated": lore_last_updated,
            "source": lore_source,
        },
        "voice": {
            "sample_count": len(voice_msgs),
            "source": "corpus" if voice_msgs else "none",
            "last_msg": voice_last_day,
        },
    }
    if thread_id:
        if lore_source == "discord-thread":
            meta["lore"]["thread_id"] = str(thread_id)
        if physical_source == "discord-thread":
            meta["physical"]["thread_id"] = str(thread_id)

    result: Dict = {
        "name": name,
        "slug": slug,
        "author_id": author_id,
        "metadata": meta,
        "physical": physical,
        "lore": lore,
        "voice_samples": voice_msgs,
    }
    if deprecated_physical_v1 is not None:
        result["deprecated_physical_v1"] = deprecated_physical_v1

    return result


def load_alias_map(path: Optional[str]) -> Dict[str, str]:
    """Load operator alias_map YAML: {name_lower: canonical_name}."""
    if not path or not Path(path).exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    return {k.lower(): v for k, v in data.items()}


def merge_all(
    tuppers: List[Dict],
    sheets: List[Dict],
    corpus: Dict[str, Dict],
    output_dir: str,
    dry_run: bool = False,
    llm_merge_fn=None,
    llm_gateway_url: str = "http://localhost:8765",
    alias_map: Optional[Dict[str, str]] = None,
) -> List[Dict]:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    tupper_map = {t["name"]: t for t in tuppers}
    sheet_map = {s["char_name"]: s for s in sheets}

    # Anchor on chars that have tupper OR discord sheet (corpus-only = no anchor)
    all_names = set(tupper_map) | set(sheet_map)

    am = alias_map or {}
    merged_chars = []
    for name in sorted(all_names):
        tupper = tupper_map.get(name)
        if not tupper:
            m = fuzzy_match_chars(name, list(tupper_map), alias_map=am)
            tupper = tupper_map.get(m) if m else None

        sheet = sheet_map.get(name)
        if not sheet:
            m = fuzzy_match_chars(name, list(sheet_map), alias_map=am)
            sheet = sheet_map.get(m) if m else None

        # Match corpus: try exact then fuzzy
        samples = corpus.get(name)
        if not samples:
            m = fuzzy_match_chars(name, list(corpus), alias_map=am)
            samples = corpus.get(m) if m else {}

        try:
            merged = merge_char(tupper, sheet, samples or {}, llm_merge_fn, llm_gateway_url)
        except Exception as e:
            print(f"Error merging '{name}': {e}", file=sys.stderr)
            continue

        merged_chars.append(merged)
        out_path = Path(output_dir) / f"{merged['slug']}.yaml"
        with open(out_path, "w", encoding="utf-8") as f:
            yaml.dump(merged, f, allow_unicode=True, sort_keys=False, indent=2)

    return merged_chars


def main() -> None:
    parser = argparse.ArgumentParser(description="Merge char sources into YAML per character")
    parser.add_argument("--tuppers", default="datasets/tupperbox/tuppers.json")
    parser.add_argument("--discord-sheets", default="datasets/discord_yokai/character_sheets_raw.jsonl")
    parser.add_argument("--excel-samples", default="datasets/yokai_rpg/operator_style_corpus.jsonl")
    parser.add_argument("--output", default="characters/")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--llm-gateway-url", default="http://localhost:8765")
    parser.add_argument("--alias-map", default=None, help="Optional YAML {name: canonical} alias overrides")
    args = parser.parse_args()

    output_dir = "/tmp/char_merge_test/" if args.dry_run else args.output

    tuppers = load_tuppers(args.tuppers)
    sheets = load_discord_sheets(args.discord_sheets)
    corpus = load_corpus_samples(args.excel_samples)
    alias_map = load_alias_map(args.alias_map)

    merged = merge_all(
        tuppers=tuppers,
        sheets=sheets,
        corpus=corpus,
        output_dir=output_dir,
        dry_run=args.dry_run,
        llm_merge_fn=llm_intelligent_merge,
        llm_gateway_url=args.llm_gateway_url,
        alias_map=alias_map,
    )
    print(f"Merged {len(merged)} characters → {output_dir}")


if __name__ == "__main__":
    main()
