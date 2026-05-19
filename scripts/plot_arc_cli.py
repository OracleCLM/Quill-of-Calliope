#!/usr/bin/env python3
"""
CLI for Quill of Calliope plot arc tracker.

Commands:
  create <arc_id> "<title>" [--char A,B,C]
  append <arc_id> <scene.md>
  summary <arc_id>
  threads <arc_id>
  continue <arc_id> [--hint "..."]
  list [--status active]
  search "<query>"
  get <arc_id>
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.calliope_shell import plot_arc


def _print_arc(arc: dict) -> None:
    print(f"Arc:     {arc['arc_id']}")
    print(f"Title:   {arc['title']}")
    print(f"Status:  {arc.get('status', 'active')}")
    print(f"Chars:   {', '.join(arc.get('chars', []))}")
    scenes = arc.get("scenes", [])
    print(f"Scenes:  {len(scenes)}")
    if scenes:
        for s in scenes:
            print(f"  [{s['scene_order']}] {s.get('scene_summary', '')[:80]}")
    summary = arc.get("summary", "")
    if summary:
        print(f"\nSummary:\n{summary}")


def cmd_create(args: argparse.Namespace) -> int:
    chars = [c.strip() for c in (args.char or "").split(",") if c.strip()]
    arc = plot_arc.create_arc(args.arc_id, args.title, chars)
    if arc:
        print(f"Created arc '{args.arc_id}': {arc['title']}")
        return 0
    print("ERROR: create_arc failed", file=sys.stderr)
    return 1


def cmd_append(args: argparse.Namespace) -> int:
    result = plot_arc.append_scene(args.arc_id, args.scene_md)
    if result:
        print(f"Appended scene {result['scene_order']}: {result.get('scene_summary', '')[:80]}")
        return 0
    print("ERROR: append_scene failed", file=sys.stderr)
    return 1


def cmd_summary(args: argparse.Namespace) -> int:
    summary = plot_arc.regenerate_summary(args.arc_id)
    if summary:
        print(f"Summary for '{args.arc_id}':\n{summary}")
        return 0
    print("ERROR: regenerate_summary failed or no scenes", file=sys.stderr)
    return 1


def cmd_threads(args: argparse.Namespace) -> int:
    threads = plot_arc.detect_open_threads(args.arc_id)
    if threads:
        print(f"Open threads for '{args.arc_id}':")
        for t in threads:
            print(f"  [{t['type']}] {t['thread']} (last scene {t['last_scene_idx']})")
    else:
        print(f"No open threads detected for '{args.arc_id}'.")
    return 0


def cmd_continue(args: argparse.Namespace) -> int:
    result = plot_arc.propose_next_scene(args.arc_id, hint=getattr(args, "hint", None))
    if result:
        print(f"Proposed next scene for '{args.arc_id}':")
        print(f"  scene_type: {result['scene_type']}")
        print(f"  prompt_seed: {result['prompt_seed']}")
        if result.get("hint_used"):
            print(f"  hint applied: {result['hint_used']}")
        return 0
    print("ERROR: propose_next_scene failed", file=sys.stderr)
    return 1


def cmd_list(args: argparse.Namespace) -> int:
    status = getattr(args, "status", None)
    arcs = plot_arc.list_arcs(status=status)
    if not arcs:
        print("No arcs found.")
        return 0
    for arc in arcs:
        print(f"  {arc['arc_id']} | {arc['title']} | {arc.get('status','active')} | chars: {', '.join(arc.get('chars',[]))}")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    results = plot_arc.search_arcs_by_topic(args.query)
    if not results:
        print("No matching arcs found.")
        return 0
    for r in results:
        print(f"  {r['arc_id']}: {r['summary_excerpt']}")
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    arc = plot_arc.get_arc(args.arc_id)
    if arc:
        _print_arc(arc)
        return 0
    print(f"ERROR: arc '{args.arc_id}' not found", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Quill of Calliope — Plot Arc CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p_create = sub.add_parser("create", help="Create a new arc")
    p_create.add_argument("arc_id")
    p_create.add_argument("title")
    p_create.add_argument("--char", default="", help="Comma-separated character names")

    p_append = sub.add_parser("append", help="Append a scene file to arc")
    p_append.add_argument("arc_id")
    p_append.add_argument("scene_md")

    p_summary = sub.add_parser("summary", help="Regenerate arc summary via LLM")
    p_summary.add_argument("arc_id")

    p_threads = sub.add_parser("threads", help="Detect open narrative threads")
    p_threads.add_argument("arc_id")

    p_continue = sub.add_parser("continue", help="Propose next scene seed")
    p_continue.add_argument("arc_id")
    p_continue.add_argument("--hint", default=None)

    p_list = sub.add_parser("list", help="List arcs")
    p_list.add_argument("--status", default=None)

    p_search = sub.add_parser("search", help="Semantic search across arcs")
    p_search.add_argument("query")

    p_get = sub.add_parser("get", help="Show arc detail")
    p_get.add_argument("arc_id")

    args = parser.parse_args()
    dispatch = {
        "create": cmd_create,
        "append": cmd_append,
        "summary": cmd_summary,
        "threads": cmd_threads,
        "continue": cmd_continue,
        "list": cmd_list,
        "search": cmd_search,
        "get": cmd_get,
    }
    return dispatch[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
