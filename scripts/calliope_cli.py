#!/usr/bin/env python3
"""Calliope CLI — character memory commands.

Usage:
  python scripts/calliope_cli.py char remember <name> <fact>
  python scripts/calliope_cli.py char recall <name> <query>
  python scripts/calliope_cli.py char forget <name> <old_fact> [--new <new_fact>]
  python scripts/calliope_cli.py char facts <name> [--scope L1|L2]
  python scripts/calliope_cli.py char list
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from app.calliope_shell.char_memory_tools import (
    char_memory_append,
    char_memory_replace,
    char_memory_recall,
    char_memory_list_facts,
)
from app.calliope_shell.char_memory import list_chars


def cmd_remember(args: argparse.Namespace) -> int:
    result = char_memory_append(args.name, args.fact, scope=args.scope)
    if result["success"]:
        print(f"✓ Fact appended [{result['scope']}] → {result['fact_id'][:8]}")
        print(f"  {result['fact_preview']}")
    else:
        print(f"✗ {result['error']}", file=sys.stderr)
        return 1
    return 0


def cmd_recall(args: argparse.Namespace) -> int:
    result = char_memory_recall(args.name, args.query, top_k=args.top_k)
    if not result["success"]:
        print(f"✗ {result['error']}", file=sys.stderr)
        return 1
    hits = result["results"]
    if not hits:
        print(f"(no facts found for {args.name!r} matching {args.query!r})")
        return 0
    print(f"Top {len(hits)} facts for {args.name!r} [{args.query!r}]:")
    for i, h in enumerate(hits, 1):
        print(f"  {i}. [{h['scope']}] score={h['score']:.3f} — {h['fact_text'][:120]}")
    return 0


def cmd_forget(args: argparse.Namespace) -> int:
    new_fact = args.new_fact or ""
    if not new_fact:
        new_fact = input(f"Replace '{args.old_fact[:50]}' with: ").strip()
        if not new_fact:
            print("Aborted.", file=sys.stderr)
            return 1

    result = char_memory_replace(
        args.name, args.old_fact, new_fact, scope=args.scope, approved=False
    )
    if result.get("requires_approval"):
        print(result["message"])
        confirm = input("Confirm? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return 0
        result = char_memory_replace(
            args.name, args.old_fact, new_fact, scope=args.scope, approved=True
        )

    if result.get("success"):
        replaced = result.get("replaced", 0)
        print(f"✓ Replaced {replaced} fact(s) in {args.name!r} [{args.scope}]")
    else:
        print(f"✗ {result.get('error', 'unknown error')}", file=sys.stderr)
        return 1
    return 0


def cmd_facts(args: argparse.Namespace) -> int:
    result = char_memory_list_facts(args.name, scope=args.scope)
    facts = result.get("facts", [])
    if not facts:
        print(f"No facts stored for {args.name!r}" + (f" [{args.scope}]" if args.scope else ""))
        return 0
    print(f"{len(facts)} fact(s) for {args.name!r}:")
    for f in facts:
        print(f"  [{f.get('scope','?')}] {f.get('fact_text','')[:120]}")
    return 0


def cmd_list(_args: argparse.Namespace) -> int:
    chars = list_chars()
    if not chars:
        print("No characters in memory DB.")
        return 0
    print(f"{len(chars)} character(s):")
    for c in chars:
        summary = c["traits_summary"] or "—"
        print(f"  • {c['name']:<25} {summary[:60]}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Calliope CLI — character memory")
    sub = p.add_subparsers(dest="entity", required=True)
    char = sub.add_parser("char", help="Character memory commands")
    csub = char.add_subparsers(dest="action", required=True)

    rem = csub.add_parser("remember", help="Append a fact to a character's memory")
    rem.add_argument("name", help="Character name")
    rem.add_argument("fact", help="Fact text to remember")
    rem.add_argument("--scope", default="L1", choices=["L1", "L2"])

    rec = csub.add_parser("recall", help="Recall facts for a character")
    rec.add_argument("name", help="Character name")
    rec.add_argument("query", help="Query text")
    rec.add_argument("--top-k", type=int, default=5)

    fgt = csub.add_parser("forget", help="Replace/update a fact")
    fgt.add_argument("name", help="Character name")
    fgt.add_argument("old_fact", help="Old fact text to replace")
    fgt.add_argument("--new", dest="new_fact", default="", help="New fact text")
    fgt.add_argument("--scope", default="L1", choices=["L1", "L2"])

    fts = csub.add_parser("facts", help="List all facts for a character")
    fts.add_argument("name", help="Character name")
    fts.add_argument("--scope", default=None, choices=["L1", "L2"])

    csub.add_parser("list", help="List all characters in memory DB")

    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    dispatch = {
        "remember": cmd_remember,
        "recall": cmd_recall,
        "forget": cmd_forget,
        "facts": cmd_facts,
        "list": cmd_list,
    }
    handler = dispatch.get(args.action)
    if handler is None:
        parser.print_help()
        sys.exit(1)
    sys.exit(handler(args))


if __name__ == "__main__":
    main()
