#!/usr/bin/env python3
"""
Token reduction benchmark: traditional "read everything" review versus the
blast-radius selection from ``blast_radius.py``.

Uses tiktoken's cl100k_base encoding for the counts (a good proxy for GLM-4 and
GPT-4 class tokenizers).

    python token_benchmark.py [changed.py ...]
"""

import sys
from pathlib import Path

import tiktoken

from blast_radius import TOOLING, build_graph, select

ENCODING = tiktoken.get_encoding("cl100k_base")
REPO = Path(__file__).parent


def count(text: str) -> int:
    return len(ENCODING.encode(text))


def main() -> None:
    changed = [a for a in sys.argv[1:] if not a.startswith("-")] or ["auth.py"]

    graph = build_graph(REPO, exclude=TOOLING)
    src_files = [m.path for m in graph.modules.values()]
    full_text = "\n".join(p.read_text(encoding="utf-8") for p in src_files)
    full_tokens = count(full_text)

    print("=" * 60)
    print("GLM Code Graph - Token Reduction Benchmark")
    print("=" * 60)
    print(f"\nRepository : {REPO}")
    print(f"Changed    : {', '.join(changed)}")

    print("\n" + "-" * 60)
    print("METHOD 1: Traditional review (read every source file)")
    print("-" * 60)
    for p in sorted(src_files, key=lambda p: -count(p.read_text(encoding='utf-8'))):
        print(f"  {p.name:<26} {count(p.read_text(encoding='utf-8')):>6,} tok")
    print(f"  {'TOTAL':<26} {full_tokens:>6,} tok  ({len(src_files)} files)")

    print("\n" + "-" * 60)
    print("METHOD 2: Blast radius (reverse dependency closure)")
    print("-" * 60)
    sel = select(REPO, changed, graph=graph)
    for f in sel.files:
        text = (REPO / f).read_text(encoding="utf-8")
        print(f"  {f:<26} {count(text):>6,} tok   {sel.reason[f]}")
    if sel.dropped:
        print(f"  (trimmed: {', '.join(sel.dropped)})")
    print(f"  {'TOTAL':<26} {sel.tokens:>6,} tok  ({len(sel.files)} files)")

    print("\n" + "=" * 60)
    print("RESULT")
    print("=" * 60)
    print(f"  files   : {len(src_files)} -> {len(sel.files)}")
    print(f"  tokens  : {full_tokens:,} -> {sel.tokens:,}")
    print(f"  reduction: {sel.token_reduction:.1f}%")


if __name__ == "__main__":
    main()
