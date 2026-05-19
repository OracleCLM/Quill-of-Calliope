#!/usr/bin/env python3
"""Idempotent migration: create plot_arcs + plot_arc_scenes tables in char_memory.db."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.calliope_shell.plot_arc import init_db

if __name__ == "__main__":
    init_db()
    print("plot_arcs schema OK")
