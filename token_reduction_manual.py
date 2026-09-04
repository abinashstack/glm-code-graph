#!/usr/bin/env python3
"""
Verbose token reduction verification.

Shows the full file list, the computed blast radius with a reason per file, and
the before/after token counts. The analysis lives in ``blast_radius.py``; this
script is just presentation.

    python token_reduction_manual.py [changed.py ...] [--budget=N] [--depth=N]
"""

import sys
from pathlib import Path

from blast_radius import TOOLING, build_graph, format_report, select

REPO = Path(__file__).parent


def main() -> None:
    changed = [a for a in sys.argv[1:] if not a.startswith("-")] or ["auth.py"]
    budget = next((int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--budget=")), None)
    depth = next((int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--depth=")), 3)

    graph = build_graph(REPO, exclude=TOOLING)
    print("=" * 64)
    print(" " * 18 + "TOKEN REDUCTION VERIFICATION")
    print("=" * 64)

    print("\n[1] Files in the graph and their first-party imports:")
    for name in sorted(graph.modules):
        mod = graph.modules[name]
        deps = ", ".join(sorted(mod.imports)) or "-"
        tag = " (test)" if mod.is_test else ""
        print(f"    {name:<28} {mod.language:<8}{tag:<8} imports: {deps}")

    edges = sum(len(v) for v in graph.forward.values())
    print(f"\n[2] {len(graph.modules)} files, {edges} first-party import edge(s)"
          f"  ({graph.stats['parsed']} parsed, {graph.stats['cached']} from cache)")

    result = select(REPO, changed, max_depth=depth, token_budget=budget, graph=graph)
    print(f"\n[3] Reviewing: {', '.join(result.review)}  (max_depth={depth})")
    print()
    print(format_report(result))


if __name__ == "__main__":
    main()
