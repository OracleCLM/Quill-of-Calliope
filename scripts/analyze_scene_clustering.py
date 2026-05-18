#!/usr/bin/env python3
"""
analyze_scene_clustering.py — Task E
Compute scene clustering statistics from *.draft.yaml files.
"""

import argparse
import re
import statistics
from datetime import datetime, timezone
from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_duration_real(s: str) -> float | None:
    """Parse '2h 18m', '50m', '1h 5m', '3h' etc. → minutes (float)."""
    s = s.strip()
    hours = 0.0
    minutes = 0.0
    h_match = re.search(r"(\d+(?:\.\d+)?)\s*h", s)
    m_match = re.search(r"(\d+(?:\.\d+)?)\s*m(?!s)", s)
    if h_match:
        hours = float(h_match.group(1))
    if m_match:
        minutes = float(m_match.group(1))
    if not h_match and not m_match:
        return None
    return hours * 60 + minutes


def ts_to_dt(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def stats_dict(values: list[float]) -> dict:
    if not values:
        return {}
    srt = sorted(values)
    n = len(srt)
    return {
        "n": n,
        "min": round(srt[0], 1),
        "max": round(srt[-1], 1),
        "mean": round(statistics.mean(srt), 1),
        "median": round(statistics.median(srt), 1),
        "p25": round(srt[max(0, int(n * 0.25) - 1)], 1),
        "p75": round(srt[min(n - 1, int(n * 0.75))], 1),
    }


def bucket_durations(durations: list[float]) -> dict[str, int]:
    buckets = {"0-30min": 0, "30-90min": 0, "90-180min": 0, "180+min": 0}
    for d in durations:
        if d < 30:
            buckets["0-30min"] += 1
        elif d < 90:
            buckets["30-90min"] += 1
        elif d < 180:
            buckets["90-180min"] += 1
        else:
            buckets["180+min"] += 1
    return buckets


def fmt_stats_row(label: str, s: dict) -> str:
    return (
        f"| {label} | {s['n']} | {s['min']} | {s['max']} | "
        f"{s['mean']} | {s['median']} | {s['p25']} | {s['p75']} |"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze scene clustering stats")
    parser.add_argument("--scenes-dir", default="scenes/", help="Directory with *.draft.yaml")
    parser.add_argument(
        "--output",
        default="docs/scene_clustering_review.md",
        help="Output markdown report path",
    )
    args = parser.parse_args()

    scenes_dir = Path(args.scenes_dir)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    yaml_files = sorted(scenes_dir.glob("*.draft.yaml"))
    if not yaml_files:
        print(f"No *.draft.yaml files found in {scenes_dir}")
        return

    # -----------------------------------------------------------------------
    # Load scenes
    # -----------------------------------------------------------------------
    records = []
    parse_errors = 0
    for f in yaml_files:
        try:
            with open(f, encoding="utf-8") as fh:
                data = yaml.safe_load(fh)
        except yaml.YAMLError:
            parse_errors += 1
            continue
        if not isinstance(data, dict):
            continue

        ts_start_raw = data.get("timestamp_start")
        ts_end_raw = data.get("timestamp_end")
        duration_raw = data.get("duration_real", "")
        msg_count = data.get("message_count", 0) or 0
        participants = data.get("participants") or []
        participant_count = len(participants)

        ts_start = ts_to_dt(ts_start_raw) if ts_start_raw else None
        ts_end = ts_to_dt(ts_end_raw) if ts_end_raw else None

        # Duration: prefer timestamps, fallback to duration_real string
        if ts_start and ts_end and ts_end > ts_start:
            duration_min = (ts_end - ts_start).total_seconds() / 60.0
        elif duration_raw:
            duration_min = parse_duration_real(str(duration_raw))
        else:
            duration_min = None

        records.append(
            {
                "scene_id": data.get("scene_id", f.stem),
                "ts_start": ts_start,
                "duration_min": duration_min,
                "msg_count": int(msg_count),
                "participant_count": participant_count,
            }
        )

    # Sort by timestamp for gap calculation
    records_with_ts = [r for r in records if r["ts_start"] is not None]
    records_with_ts.sort(key=lambda r: r["ts_start"])

    # Gap between consecutive scenes
    gaps: list[float] = []
    for i in range(1, len(records_with_ts)):
        prev = records_with_ts[i - 1]
        curr = records_with_ts[i]
        if prev["ts_start"] is not None and curr["ts_start"] is not None:
            gap = (curr["ts_start"] - prev["ts_start"]).total_seconds() / 60.0
            if gap >= 0:
                gaps.append(gap)

    durations = [r["duration_min"] for r in records if r["duration_min"] is not None]
    msg_counts = [r["msg_count"] for r in records if r["msg_count"] > 0]
    participant_counts = [r["participant_count"] for r in records if r["participant_count"] > 0]

    s_dur = stats_dict(durations)
    s_gap = stats_dict(gaps)
    s_msg = stats_dict(msg_counts)
    s_par = stats_dict(participant_counts)

    buckets = bucket_durations(durations)

    total = len(records)
    print(f"Loaded {total} scenes, {len(records_with_ts)} with timestamps")
    print(f"Duration stats: {s_dur}")
    print(f"Gap stats: {s_gap}")
    print(f"Msg stats: {s_msg}")
    print(f"Participant stats: {s_par}")
    print(f"Duration buckets: {buckets}")

    # -----------------------------------------------------------------------
    # Serialise stats for external use (printed for MCP prompt building)
    # -----------------------------------------------------------------------
    stats_summary = (
        f"Duration (min): min={s_dur.get('min')}, max={s_dur.get('max')}, "
        f"mean={s_dur.get('mean')}, median={s_dur.get('median')}, "
        f"p25={s_dur.get('p25')}, p75={s_dur.get('p75')}\n"
        f"Gap between scenes (min): min={s_gap.get('min')}, max={s_gap.get('max')}, "
        f"mean={s_gap.get('mean')}, median={s_gap.get('median')}, "
        f"p25={s_gap.get('p25')}, p75={s_gap.get('p75')}\n"
        f"Message count: min={s_msg.get('min')}, max={s_msg.get('max')}, "
        f"mean={s_msg.get('mean')}, median={s_msg.get('median')}, "
        f"p25={s_msg.get('p25')}, p75={s_msg.get('p75')}\n"
        f"Participant count: min={s_par.get('min')}, max={s_par.get('max')}, "
        f"mean={s_par.get('mean')}, median={s_par.get('median')}, "
        f"p25={s_par.get('p25')}, p75={s_par.get('p75')}\n"
        f"Duration buckets: {buckets}"
    )

    # -----------------------------------------------------------------------
    # Write report (placeholder for Groq section — filled externally)
    # -----------------------------------------------------------------------
    header = f"""# Scene Clustering Review — Quill of Calliope M1
Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}
Total scenes: {total} | Scenes with timestamps: {len(records_with_ts)}

## 1. Statistics Table

| Metric | N | Min | Max | Mean | Median | P25 | P75 |
|--------|---|-----|-----|------|--------|-----|-----|
{fmt_stats_row("Duration (min)", s_dur)}
{fmt_stats_row("Gap between scenes (min)", s_gap)}
{fmt_stats_row("Message count", s_msg)}
{fmt_stats_row("Participant count", s_par)}

## 2. Duration Histogram

| Bucket | Count | % |
|--------|-------|---|
| 0–30 min | {buckets['0-30min']} | {buckets['0-30min']/len(durations)*100:.1f}% |
| 30–90 min | {buckets['30-90min']} | {buckets['30-90min']/len(durations)*100:.1f}% |
| 90–180 min | {buckets['90-180min']} | {buckets['90-180min']/len(durations)*100:.1f}% |
| 180+ min | {buckets['180+min']} | {buckets['180+min']/len(durations)*100:.1f}% |

## 3. Recalibration Recommendation

<!-- GROQ_SECTION_PLACEHOLDER -->

## 4. M1 Defaults & Discord Recommendation

**Current M1 defaults**: gap ≥ 30 min OR msg ≥ 10 → new scene boundary.

<!-- GROQ_M1_PLACEHOLDER -->

---
*Raw stats for MCP prompt:*
```
{stats_summary}
```
"""

    output_path.write_text(header, encoding="utf-8")
    print(f"\nReport written to {output_path}")
    print(f"\n--- STATS_FOR_MCP ---\n{stats_summary}\n--- END_STATS ---")


if __name__ == "__main__":
    main()
