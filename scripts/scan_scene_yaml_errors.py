#!/usr/bin/env python3
"""Scan scenes/*.draft.yaml for YAML syntax errors and report."""
import argparse
import glob
import os
import yaml


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenes-dir", default="scenes/")
    parser.add_argument("--output", default=".planning/SCENE_YAML_ERRORS.md")
    args = parser.parse_args()

    files = sorted(glob.glob(os.path.join(args.scenes_dir, "*.yaml")))
    errors = []
    for path in files:
        try:
            with open(path, encoding="utf-8") as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            mark = getattr(e, "problem_mark", None)
            line = mark.line + 1 if mark else "?"
            col = mark.column + 1 if mark else "?"
            prob = getattr(e, "problem", str(e))
            errors.append({"path": path, "line": line, "col": col, "problem": prob})

    # write report
    with open(args.output, "w", encoding="utf-8") as out:
        out.write("# Scene YAML Syntax Errors\n\n")
        out.write(f"Scanned: {len(files)} files — Errors: {len(errors)}\n\n")
        if not errors:
            out.write("No errors found.\n")
        else:
            out.write("| File | Line | Col | Problem |\n")
            out.write("|------|------|-----|---------|\n")
            for e in errors:
                fname = os.path.basename(e["path"])
                prob = e["problem"].replace("|", "\\|")
                out.write(f"| {fname} | {e['line']} | {e['col']} | {prob} |\n")
            out.write("\n## Suggested Fix\n\n")
            out.write(
                "Most common cause: unquoted `:` or `#` in summary/title text. "
            )
            out.write("Wrap the field value in double quotes or use block scalar `|`.\n\n")
            out.write("Operator decision required before modifying originals.\n")

    print(f"Done. {len(errors)} errors found. Report: {args.output}")


if __name__ == "__main__":
    main()
