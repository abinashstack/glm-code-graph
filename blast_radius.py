#!/usr/bin/env python3
"""
blast_radius.py -- the minimal set of files a reviewer must read for a change.

Multi-language: Python is parsed with the stdlib ``ast`` (no dependency).
JavaScript, TypeScript and Go are parsed with tree-sitter when the matching
grammar package is installed (``pip install tree-sitter tree-sitter-javascript
tree-sitter-typescript tree-sitter-go``); without it, files in that language
are skipped (isolated nodes) rather than crashing the build.

Incremental: each file's parse result is cached by content hash in
``.blast_radius_cache.json`` at the repo root. Rebuilding the graph re-parses
only files whose content changed since the last run; import *resolution* (a
raw import specifier -> a repo-relative path) is always recomputed against the
current file set, so a newly added file is picked up even though the file that
imports it wasn't touched and its parse came from cache.

Differences from the original one-hop ``import`` regex scan this replaces:

  * Direction is reversed. "What does my change break" needs the modules that
    import the changed one (its callers), not the modules it imports.
  * Imports are read from a real parser (AST / tree-sitter), so aliased
    imports, ``from x import *`` and function-local imports are all found.
  * The reverse walk is transitive but bounded by ``max_depth``.
  * When the result overflows ``token_budget`` it is trimmed as a
    priority-prefix cut, ranked by hop distance then PageRank. Changed files
    are never dropped.
  * Tests that import any impacted module are pulled in as review context.
  * Nodes are keyed by repo-relative path, not filename stem -- two files
    named ``util.py`` in different directories do not collide.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path

TEST_PREFIXES = ("test_",)
TEST_SUFFIXES = ("_test",)

# The analysis/benchmark scripts are not part of the codebase under review.
# (token_benchmark.js is the old Node.js port of the same verification script.)
TOOLING = {
    "blast_radius.py",
    "count_bytes.py",
    "token_benchmark.py",
    "token_benchmark.js",
    "token_reduction_manual.py",
    "test_blast_radius.py",
}

SKIP_DIRS = {"__pycache__", "node_modules", ".git", "vendor", ".venv", "venv", "dist", "build"}

EXT_LANGUAGE = {
    ".py": "python",
    ".js": "js", ".jsx": "js", ".mjs": "js", ".cjs": "js",
    ".ts": "ts", ".mts": "ts", ".cts": "ts",
    ".tsx": "tsx",
    ".go": "go",
}
_JS_RESOLVE_EXTS = (".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx")
_GRAMMAR_PACKAGE = {"js": "tree-sitter-javascript", "ts": "tree-sitter-typescript",
                    "tsx": "tree-sitter-typescript", "go": "tree-sitter-go"}

CACHE_VERSION = 2
CACHE_FILENAME = ".blast_radius_cache.json"


@dataclass
class Module:
    path: Path
    language: str
    raw_imports: list[str] = field(default_factory=list)   # unresolved specifiers, as parsed
    is_test: bool = False
    imports: set[str] = field(default_factory=set)          # resolved repo-relative paths, filled by build_graph


@dataclass
class Graph:
    modules: dict[str, Module]      # keyed by repo-relative posix path
    forward: dict[str, set[str]]    # path -> paths it imports
    reverse: dict[str, set[str]]    # path -> paths that import it
    stats: dict[str, int] = field(default_factory=dict)   # {"parsed": n, "cached": n}


@dataclass
class Selection:
    review: list[str]
    files: list[str]
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


# ---------------------------------------------------------------- test detection


def _is_test(rel: str, language: str) -> bool:
    stem = Path(rel).stem
    if language == "python":
        return stem.startswith(TEST_PREFIXES) or stem.endswith(TEST_SUFFIXES)
    if language == "go":
        return stem.endswith("_test")
    if language in ("js", "ts", "tsx"):
        low = rel.lower()
        return ".test." in low or ".spec." in low or "/__tests__/" in low or low.startswith("__tests__/")
    return False


# ---------------------------------------------------------------- extraction (per language, cached)


def _extract_python(data: bytes, rel: str) -> list[str]:
    try:
        tree = ast.parse(data.decode("utf-8"), filename=rel)
    except (SyntaxError, UnicodeDecodeError):
        return []
    specs: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            specs.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                # `from . import x` / `from .pkg import y` / `from .. import z` --
                # resolvable exactly, relative to the importing file's directory.
                # Encoded (not just `alias.name`) so the resolver has level/module
                # to walk to the right directory instead of a repo-wide name guess.
                specs.extend(f"REL:{node.level}:{node.module or ''}:{alias.name}"
                             for alias in node.names)
            elif node.module:
                specs.append(node.module)
    return specs


_TS_PARSERS: dict[str, object] = {}
_TS_WARNED: set[str] = set()


def _get_ts_parser(language: str):
    if language in _TS_PARSERS:
        return _TS_PARSERS[language]
    parser = None
    try:
        from tree_sitter import Language, Parser
        if language == "js":
            import tree_sitter_javascript as grammar
            parser = Parser(Language(grammar.language()))
        elif language == "ts":
            import tree_sitter_typescript as grammar
            parser = Parser(Language(grammar.language_typescript()))
        elif language == "tsx":
            import tree_sitter_typescript as grammar
            parser = Parser(Language(grammar.language_tsx()))
        elif language == "go":
            import tree_sitter_go as grammar
            parser = Parser(Language(grammar.language()))
    except ImportError:
        if language not in _TS_WARNED:
            _TS_WARNED.add(language)
            pkg = _GRAMMAR_PACKAGE.get(language, "tree-sitter-<lang>")
            print(f"  (skipping .{language} files: pip install tree-sitter {pkg} to parse them)",
                  file=sys.stderr)
    _TS_PARSERS[language] = parser
    return parser


def _string_fragment(string_node) -> str | None:
    for child in string_node.children:
        if child.type in ("string_fragment", "interpreted_string_literal_content"):
            return child.text.decode("utf-8", "replace")
    return None


def _walk_js(root_node, out: list[str]) -> None:
    # Iterative, not recursive: a pathological (e.g. generated/minified) source
    # file can nest thousands of levels deep, which would blow Python's call
    # stack -- an explicit, heap-allocated stack has no such limit.
    stack = [root_node]
    while stack:
        node = stack.pop()
        if node.type in ("import_statement", "export_statement"):
            for child in node.children:
                if child.type == "string":
                    frag = _string_fragment(child)
                    if frag:
                        out.append(frag)
        elif node.type == "call_expression" and node.children:
            fn = node.children[0]
            if (fn.type == "identifier" and fn.text == b"require") or fn.type == "import":
                args = next((c for c in node.children if c.type == "arguments"), None)
                if args:
                    for c in args.children:
                        if c.type == "string":
                            frag = _string_fragment(c)
                            if frag:
                                out.append(frag)
        stack.extend(node.children)


def _walk_go(root_node, out: list[str]) -> None:
    stack = [root_node]   # iterative for the same reason as _walk_js
    while stack:
        node = stack.pop()
        if node.type == "import_spec":
            for child in node.children:
                if child.type == "interpreted_string_literal":
                    frag = _string_fragment(child)
                    if frag:
                        out.append(frag)
        stack.extend(node.children)


def _extract(language: str, data: bytes, rel: str) -> list[str]:
    if language == "python":
        return _extract_python(data, rel)
    parser = _get_ts_parser(language)
    if parser is None:
        return []
    tree = parser.parse(data)
    out: list[str] = []
    (_walk_go if language == "go" else _walk_js)(tree.root_node, out)
    return out


# ---------------------------------------------------------------- resolution (uncached: needs the live file set)


@dataclass
class IndexData:
    all_paths: set[str]
    py_stem_index: dict[str, list[str]]
    go_module: str | None


def _read_go_module(root: Path) -> str | None:
    gomod = root / "go.mod"
    if not gomod.exists():
        return None
    for line in gomod.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("module "):
            return line[len("module "):].strip()
    return None


def _build_index(root: Path, modules: dict[str, Module]) -> IndexData:
    py_stem_index: dict[str, list[str]] = defaultdict(list)
    for rel, mod in modules.items():
        if mod.language == "python":
            py_stem_index[Path(rel).stem].append(rel)
    return IndexData(set(modules), dict(py_stem_index), _read_go_module(root))


def _resolve_python_relative(level: int, module: str, name: str, file_rel: str, idx: IndexData) -> list[str]:
    # `from . import x` (level=1) is relative to the importing file's own
    # directory; each extra level (`from .. import x`) steps up one more
    # parent. Unlike the bare-name case below, this is fully unambiguous --
    # it never needs the repo-wide stem index and so never collides with a
    # same-named file in an unrelated package.
    base_dir = Path(file_rel).parent
    for _ in range(max(level - 1, 0)):
        base_dir = base_dir.parent
    search_dir = (base_dir / module) if module else base_dir
    for candidate in (search_dir / f"{name}.py", search_dir / name / "__init__.py"):
        key = candidate.as_posix()
        if key in idx.all_paths:
            return [key]
    if module:   # `name` may be a symbol defined in `module` itself, not a submodule of it
        for candidate in (base_dir / f"{module}.py", base_dir / module / "__init__.py"):
            key = candidate.as_posix()
            if key in idx.all_paths:
                return [key]
    return []


def _resolve_python(raw: str, file_rel: str, idx: IndexData) -> list[str]:
    if raw.startswith("REL:"):
        _, level_s, module, name = raw.split(":", 3)
        return _resolve_python_relative(int(level_s), module, name, file_rel, idx)
    # Bare/absolute import (`import a.b`, `from a.b import c`): resolved by a
    # repo-wide match on the first dotted segment's filename stem. This is a
    # best-effort heuristic for a flat or simple package layout -- if two
    # files anywhere in the repo share that stem, resolution is genuinely
    # ambiguous without modeling sys.path/package structure, so it's skipped
    # rather than guessing which one.
    matches = idx.py_stem_index.get(raw.split(".")[0])
    return matches if matches and len(matches) == 1 else []


def _resolve_js(raw: str, file_rel: str, idx: IndexData) -> list[str]:
    if not raw.startswith((".", "/")):
        return []   # bare specifier -> an npm package, not first-party
    if raw.startswith("/"):
        combined = raw
    else:
        base = Path(file_rel).parent.as_posix()
        combined = raw if base == "." else f"{base}/{raw}"
    parts: list[str] = []
    for part in combined.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        parts.append(part)
    norm = "/".join(parts)
    candidates = [norm, *(f"{norm}{ext}" for ext in _JS_RESOLVE_EXTS),
                  *(f"{norm}/index{ext}" for ext in _JS_RESOLVE_EXTS)]
    for c in candidates:
        if c in idx.all_paths:
            return [c]
    return []


def _resolve_go(raw: str, idx: IndexData) -> list[str]:
    # Go imports name a *package* (directory); every non-test file in that
    # directory is a plausible impact target, so this fans out to all of them.
    if not idx.go_module or raw != idx.go_module and not raw.startswith(idx.go_module + "/"):
        return []
    target_dir = raw[len(idx.go_module):].lstrip("/")
    return sorted(
        p for p in idx.all_paths
        if p.endswith(".go") and not p.endswith("_test.go")
        and Path(p).parent.as_posix() == (target_dir or ".")
    )


def _resolve(language: str, raw: str, file_rel: str, idx: IndexData) -> list[str]:
    if language == "python":
        return _resolve_python(raw, file_rel, idx)
    if language in ("js", "ts", "tsx"):
        return _resolve_js(raw, file_rel, idx)
    if language == "go":
        return _resolve_go(raw, idx)
    return []


# ---------------------------------------------------------------- cache


def _fingerprint(data: bytes) -> str:
    return hashlib.sha1(data).hexdigest()


def _load_cache(root: Path) -> dict[str, dict]:
    path = root / CACHE_FILENAME
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return obj.get("files", {}) if obj.get("version") == CACHE_VERSION else {}


def _save_cache(root: Path, files: dict[str, dict]) -> None:
    try:
        (root / CACHE_FILENAME).write_text(
            json.dumps({"version": CACHE_VERSION, "files": files}), encoding="utf-8"
        )
    except OSError:
        pass   # a read-only tree just loses incremental caching, not correctness


# ---------------------------------------------------------------- graph build


def build_graph(root: str | Path, exclude: set[str] | None = None, use_cache: bool = True) -> Graph:
    root = Path(root).resolve()
    exclude = exclude or set()
    # SKIP_DIRS must be checked against the path *within the repo*, not the
    # absolute path -- otherwise checking out this repo itself under an
    # ancestor directory named e.g. build/ or vendor/ (a common CI layout)
    # would match every file and silently empty the whole graph.
    paths = [
        p for p in sorted(root.rglob("*"))
        if p.is_file() and p.suffix in EXT_LANGUAGE
        and not (set(p.relative_to(root).parts) & SKIP_DIRS) and p.name not in exclude
    ]

    cache = _load_cache(root) if use_cache else {}
    new_cache: dict[str, dict] = {}
    modules: dict[str, Module] = {}
    stats = {"parsed": 0, "cached": 0}

    for path in paths:
        rel = path.relative_to(root).as_posix()
        language = EXT_LANGUAGE[path.suffix]
        data = path.read_bytes()
        fp = _fingerprint(data)
        cached = cache.get(rel)
        if cached and cached.get("fingerprint") == fp and cached.get("language") == language:
            raw_imports = cached["raw_imports"]
            stats["cached"] += 1
        else:
            raw_imports = _extract(language, data, rel)
            stats["parsed"] += 1
        new_cache[rel] = {"fingerprint": fp, "language": language, "raw_imports": raw_imports}
        modules[rel] = Module(path=path, language=language, raw_imports=raw_imports,
                               is_test=_is_test(rel, language))

    if use_cache:
        _save_cache(root, new_cache)

    # Resolution always runs fresh against the current file set: a file whose
    # own parse came from cache can still gain a newly-resolvable import when
    # some *other* file is added or removed.
    idx = _build_index(root, modules)
    forward: dict[str, set[str]] = defaultdict(set)
    reverse: dict[str, set[str]] = defaultdict(set)
    for rel, mod in modules.items():
        resolved: set[str] = set()
        for raw in mod.raw_imports:
            resolved.update(_resolve(mod.language, raw, rel, idx))
        resolved.discard(rel)
        mod.imports = resolved
        for dep in resolved:
            forward[rel].add(dep)
            reverse[dep].add(rel)

    return Graph(modules, forward, reverse, stats)


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


def _to_relpath(root: Path, given: str) -> str:
    p = Path(given)
    abs_p = p if p.is_absolute() else (root / p)
    try:
        return abs_p.resolve().relative_to(root).as_posix()
    except ValueError:
        return p.as_posix()


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
    seeds = [_to_relpath(root, c) for c in changed]
    unknown = [s for s in seeds if s not in graph.modules]
    if unknown:
        raise ValueError(f"not a file in {root}: {', '.join(unknown)}")

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

    sizes = {n: _count_tokens(graph.modules[n].path.read_text(encoding="utf-8", errors="replace"))
             for n in ordered}

    # Priority-prefix cut: keep the longest prefix of `ordered` that fits the
    # budget. Once one file is dropped, every lower-priority file is dropped
    # too. Changed files (kind 0) are always kept, even over budget.
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

    all_src = "\n".join(
        m.path.read_text(encoding="utf-8", errors="replace") for m in graph.modules.values()
    )

    return Selection(
        review=seeds,
        files=kept,
        reason={n: reason[n] for n in kept},
        dropped=dropped,
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
