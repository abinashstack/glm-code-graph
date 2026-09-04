#!/usr/bin/env python3
"""
blast_radius.py -- the minimal set of files a reviewer must read for a change.

Replaces the one-hop regex ``import`` scan used by the demo scripts. Differences:

  * Direction is reversed. "What does my change break" needs the modules that
    import the changed one (its callers), not the modules it imports.
  * Imports are read from the AST, so aliased, ``from x import *`` and
    function-local imports (``from config import SECRET_KEY`` inside a method)
    are all found. Line-prefix matching misses those silently.
  * The reverse walk is transitive but bounded by ``max_depth``.
  * When the result overflows ``token_budget`` it is trimmed from the least
    important end, ranked by hop distance then PageRank. Changed files are
    never dropped.
  * Tests that import any impacted module are pulled in as review context.

No third-party dependencies. ``tiktoken`` is used for the token count when it is
installed, otherwise a bytes/4 estimate.
"""

from __future__ import annotations

import ast
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

TEST_PREFIXES = ("test_",)
TEST_SUFFIXES = ("_test",)

# The analysis/benchmark scripts are not part of the codebase under review.
TOOLING = {
    "blast_radius.py",
    "count_bytes.py",
    "token_benchmark.py",
    "token_reduction_manual.py",
    "test_blast_radius.py",
}


@dataclass
class Module:
    name: str
    path: Path
    imports: set[str] = field(default_factory=set)   # first-party module names
    is_test: bool = False


@dataclass
class Graph:
    modules: dict[str, Module]
    forward: dict[str, set[str]]   # module -> modules it imports
    reverse: dict[str, set[str]]   # module -> modules that import it


@dataclass
class Selection:
    review: list[str]
    files: list[str]              # ordered, repo-relative, changed files first
    reason: dict[str, str]
    dropped: list[str]
    tokens: int
    full_tokens: int
    full_files: int

    @property
    def token_reduction(self) -> float:
        if not self.full_tokens:
            return 0.0
        return (self.full_tokens - self.tokens) / self.full_tokens * 100


def _is_test(stem: str) -> bool:
    return stem.startswith(TEST_PREFIXES) or stem.endswith(TEST_SUFFIXES)


def parse_module(path: Path, first_party: set[str]) -> Module:
    mod = Module(name=path.stem, path=path, is_test=_is_test(path.stem))
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, UnicodeDecodeError):
        return mod

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                head = alias.name.split(".")[0]
                if head in first_party:
                    mod.imports.add(head)
        elif isinstance(node, ast.ImportFrom):
            # `from config import X`  ->  node.module == "config"
            if node.module:
                head = node.module.split(".")[0]
                if head in first_party:
                    mod.imports.add(head)
            # `from . import config`  ->  names carry the module
            if node.level:
                for alias in node.names:
                    if alias.name in first_party:
                        mod.imports.add(alias.name)

    mod.imports.discard(mod.name)
    return mod


def build_graph(root: str | Path, exclude: set[str] | None = None) -> Graph:
    root = Path(root).resolve()
    exclude = exclude or set()
    paths = [
        p for p in sorted(root.rglob("*.py"))
        if "__pycache__" not in p.parts and p.name not in exclude
    ]
    first_party = {p.stem for p in paths}
    modules = {p.stem: parse_module(p, first_party) for p in paths}

    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for mod in modules.values():
        for dep in mod.imports:
            forward[mod.name].add(dep)
            reverse[dep].add(mod.name)
    return Graph(modules, forward, reverse)


def pagerank(graph: Graph, damping: float = 0.85, iterations: int = 40) -> dict[str, float]:
    """PageRank on the forward graph -- a module ranks high when many (and
    important) modules depend on it. A "how foundational is this file" score."""
    nodes = list(graph.modules)
    n = len(nodes)
    if n == 0:
        return {}
    out = {k: (graph.forward.get(k) or set()) for k in nodes}
    dangling = [k for k in nodes if not out[k]]
    rank = {k: 1.0 / n for k in nodes}
    for _ in range(iterations):
        leaked = damping * sum(rank[d] for d in dangling) / n
        nxt = {k: (1.0 - damping) / n + leaked for k in nodes}
        for k in nodes:
            if out[k]:
                share = damping * rank[k] / len(out[k])
                for target in out[k]:
                    nxt[target] += share
        rank = nxt
    return rank


def _reverse_reachable(graph: Graph, seeds: list[str], max_depth: int) -> dict[str, int]:
    dist: dict[str, int] = {s: 0 for s in seeds if s in graph.modules}
    queue = deque(dist)
    while queue:
        cur = queue.popleft()
        if dist[cur] >= max_depth:
            continue
        for importer in graph.reverse.get(cur, ()):
            if importer not in dist:
                dist[importer] = dist[cur] + 1
                queue.append(importer)
    return dist


def _count_tokens(text: str) -> int:
    try:
        import tiktoken
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    except Exception:
        return len(text.encode("utf-8")) // 4


def select(
    root: str | Path,
    changed: list[str],
    max_depth: int = 3,
    token_budget: int | None = None,
    exclude: set[str] | None = None,
    graph: Graph | None = None,
) -> Selection:
    root = Path(root).resolve()
    graph = graph if graph is not None else build_graph(root, exclude)
    seeds = [Path(c).stem for c in changed]
    unknown = [s for s in seeds if s not in graph.modules]
    if unknown:
        raise ValueError(f"not a module in {root}: {', '.join(unknown)}")

    rank = pagerank(graph)
    impacted = _reverse_reachable(graph, seeds, max_depth)

    # kind: 0 changed, 1 reverse-impacted, 2 direct dependency, 3 covering test
    kind: dict[str, int] = {}
    depth: dict[str, int] = {}
    for name, d in impacted.items():
        kind[name] = 0 if d == 0 else 1
        depth[name] = d
    for seed in seeds:                                    # 1-hop forward: context for the change
        for dep in graph.forward.get(seed, ()):
            kind.setdefault(dep, 2)
            depth.setdefault(dep, 1)
    for name, mod in graph.modules.items():               # tests over impacted code
        if mod.is_test and mod.imports & impacted.keys() and name not in kind:
            kind[name] = 3
            depth[name] = 1

    def sort_key(name: str):
        return (kind[name], depth[name], -rank.get(name, 0.0), name)

    ordered = sorted(kind, key=sort_key)

    reason_text = {
        0: "changed",
        1: "imports the change",
        2: "dependency of the change",
        3: "test over impacted code",
    }
    reason = {
        n: (reason_text[1] + f" ({depth[n]} hop{'s' if depth[n] != 1 else ''} up)")
        if kind[n] == 1 else reason_text[kind[n]]
        for n in ordered
    }

    sizes = {n: _count_tokens(graph.modules[n].path.read_text(encoding="utf-8")) for n in ordered}

    # Priority-prefix cut: keep the longest prefix of `ordered` that fits the
    # budget. Once one file is dropped, every lower-priority file is dropped too,
    # so the kept set is never missing a file more important than one it keeps.
    # Changed files (kind 0) are always kept, even over budget.
    kept, dropped, running, over = [], [], 0, False
    for name in ordered:
        if kind[name] == 0:
            kept.append(name)
            running += sizes[name]
            continue
        if over or (token_budget is not None and running + sizes[name] > token_budget):
            over = True
            dropped.append(name)
            continue
        kept.append(name)
        running += sizes[name]

    all_src = "\n".join(m.path.read_text(encoding="utf-8") for m in graph.modules.values())

    def rel(name: str) -> str:
        return graph.modules[name].path.relative_to(root).as_posix()

    return Selection(
        review=[rel(s) for s in seeds],
        files=[rel(n) for n in kept],
        reason={rel(n): reason[n] for n in kept},
        dropped=[rel(n) for n in dropped],
        tokens=running,
        full_tokens=_count_tokens(all_src),
        full_files=len(graph.modules),
    )


def format_report(sel: Selection) -> str:
    lines = [
        "=" * 64,
        f"  BLAST RADIUS  ({', '.join(sel.review)})",
        "=" * 64,
        "",
        f"  read {len(sel.files)} file(s), skip {sel.full_files - len(sel.files)}:",
        "",
    ]
    width = max((len(f) for f in sel.files), default=0)
    for f in sel.files:
        lines.append(f"    {f:<{width}}  {sel.reason[f]}")
    if sel.dropped:
        lines += ["", f"  trimmed to fit token budget: {', '.join(sel.dropped)}"]
    lines += [
        "",
        "-" * 64,
        f"  tokens   {sel.tokens:>8,}   (full review: {sel.full_tokens:,})",
        f"  reduction {sel.token_reduction:>6.1f}%",
        "=" * 64,
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    changed = args or ["auth.py"]
    budget = None
    for a in sys.argv[1:]:
        if a.startswith("--budget="):
            budget = int(a.split("=", 1)[1])
    result = select(Path(__file__).parent, changed, token_budget=budget, exclude=TOOLING)
    print(format_report(result))
