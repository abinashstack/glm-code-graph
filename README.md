# GLM Code Graph - Token Reduction Demonstration

![token reduction](https://img.shields.io/badge/token_reduction-48%25_on_4--file_demo-2f7d4f)

## Overview

This repository demonstrates **blast radius analysis** for code review: instead of
feeding an LLM the whole codebase, feed it only the files a given change can affect.
The analysis lives in [`blast_radius.py`](blast_radius.py); the other scripts are
presentation over it.

## What is GLM Code Graph?

Given a set of changed files, GLM Code Graph returns the minimal set of files a
reviewer (human or model) needs to read:

1. **Reverse dependency closure.** The modules that *import* the changed one, then
   the modules that import *those*, bounded by `--depth` (default 3). This is the
   "what could my change break" set — the opposite direction from the change's own
   imports.
2. **Plus direct dependencies.** The modules the change itself imports (one hop),
   as context for understanding the change.
3. **Plus covering tests.** Any test module that imports something in the closure.
4. **Trimmed to a token budget.** When the set overflows `--budget`, the
   lowest-priority files (farthest hop, lowest PageRank) are dropped. Changed
   files are never dropped.

Imports are read from a real parser (AST for Python, tree-sitter for the
others), so aliased imports, `from x import *`, and function-local imports are
all detected — a line-prefix string scan misses them.

**Multi-language.** Python needs nothing extra (stdlib `ast`). JavaScript,
TypeScript and Go are parsed with [tree-sitter](https://tree-sitter.github.io/)
when the matching grammar is installed:

```bash
pip install tree-sitter tree-sitter-javascript tree-sitter-typescript tree-sitter-go
```

Without a grammar installed, files in that language are skipped (isolated
nodes) rather than crashing the build — the graph degrades, it doesn't break.

**Incremental.** Each file's parse result is cached by content hash in
`.blast_radius_cache.json`. Rebuilding re-parses only files that changed since
the last run; import *resolution* is always recomputed against the live file
set, so adding a new file is picked up immediately even for files that weren't
touched and whose parse came from cache.

### Example

```
$ python token_benchmark.py auth.py

METHOD 1: Traditional review (read every source file)
  auth.py 487  database.py 454  config.py 403  user.py 375   TOTAL 1,719 tok (4 files)

METHOD 2: Blast radius
  auth.py 487   changed
  config.py 403 dependency of the change                     TOTAL   890 tok (2 files)

  reduction: 48.2%
```

The reduction scales with repo size: the same 2-file radius is ~48% of a 4-file
toy repo but 90%+ of a real one. The engineering that matters on real code is
*bounding* the closure, which this demo's tiny graph never stresses.

## Installation

### Prerequisites

- Git
- Python 3.10+ (for the verification scripts)
- Optional: `pip install -r requirements-languages.txt` for JS/TS/Go parsing
  and exact token counts. Python-only analysis needs nothing extra.

### Quick Setup

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/glm-code-graph-demo.git
cd glm-code-graph-demo
```

2. **Verify installation:**
```bash
python count_bytes.py
```

### Directory Structure

```
glm-code-graph/
├── README.md
├── blast_radius.py             # The analysis: multi-language graph, cache, reverse closure, trim
├── test_blast_radius.py        # Verification (python test_blast_radius.py)
├── count_bytes.py              # CLI: reduction for a change
├── token_reduction_manual.py   # CLI: verbose, shows the graph
├── token_benchmark.py          # CLI: side-by-side token comparison (needs tiktoken)
├── .claude/skills/blast-radius/SKILL.md  # Claude Code / GLM-skills-format skill
├── auth.py                     # Mock Python: auth + tokens (imports config.py)
├── config.py                   # Mock Python: configuration
├── user.py                     # Mock Python: user service
├── database.py                 # Mock Python: database layer
├── go.mod                      # Mock Go module ("glmdemo")
├── service/
│   ├── handler.go              # Mock Go: imports the util package
│   └── util/helper.go          # Mock Go: a separate package
└── web/
    ├── utils.js                 # Mock JS: no first-party imports
    ├── app.js                   # Mock JS: `require('./utils')`
    └── format.ts                # Mock TS: `import ... from './utils.js'`
```

The `.ps1`, `.bat`, `.sh` and `.cs` files are older single-file ports of the
byte-count estimate and are not wired to `blast_radius.py`.
`.blast_radius_cache.json` is generated at the repo root on first run and is
gitignored.

## How It Works

`blast_radius.build_graph()` walks the repo, and for each `.py`/`.js`/`.jsx`/
`.ts`/`.tsx`/`.go` file:

1. Hashes its content and checks `.blast_radius_cache.json` for a hit. On a
   hit, reuses the cached raw import list; on a miss, parses fresh (`ast` for
   Python, tree-sitter for the rest) and updates the cache entry.
2. Resolves each raw import specifier against the *current* repo file set —
   Python by bare-name match on file stem, JS/TS by relative-path resolution
   (`./x`, `../x/y`, trying `index.*` and known extensions), Go by `go.mod`'s
   module path (an import resolves to every non-test file in that package
   directory, since Go imports name a package, not a file).

Nodes are keyed by repo-relative path, not filename stem, so two files named
`util.py` in different packages don't collide. Edges are `A imports B`; the
reverse index gives `B is imported by A`.

`blast_radius.select(root, changed, max_depth, token_budget)` then:

1. BFS over the **reverse** edges from each changed module, tagging every module
   with its hop distance (stop at `max_depth`).
2. Adds one forward hop (direct dependencies) and covering test modules.
3. Ranks by `(hop distance, -PageRank)` and drops from the tail until the token
   total fits `token_budget`.

`PageRank` is computed on the forward graph — a module scores high when many
important modules depend on it — and is used only for tie-breaking during the
trim.

### Token Calculation

Counts use `tiktoken`'s `cl100k_base` encoding when installed, otherwise a
`bytes / 4` estimate.

### API

```python
from blast_radius import select, format_report, TOOLING

# exclude=TOOLING drops this repo's own analysis scripts from the graph, so the
# baseline is just the mock auth code (auth/config/user/database). The CLIs do this.
sel = select(".", ["auth.py"], max_depth=3, token_budget=8000, exclude=TOOLING)
print(format_report(sel))
print(sel.files)            # ['auth.py', 'config.py']
print(round(sel.token_reduction, 1))  # 48.2
```

## Usage

### Run Verification Scripts

**Windows:**
```bash
# PowerShell
powershell -ExecutionPolicy Bypass -File TokenReduction.ps1

# Batch
token_reduction.bat
```

**Linux/Mac:**
```bash
# Shell
bash token_calc.sh

# Python
python count_bytes.py
```

### View Results

Run any verification script to see:
- Total files and size
- Blast radius calculation
- Token reduction metrics
- Cost savings

## Cost Savings Calculator

Based on GLM-4 pricing ($0.00001/token):

| Reviews Per Month | Tokens Saved | Dollar Savings |
|-------------------|--------------|----------------|
| 10                | 69,520       | $0.70          |
| 100               | 695,200      | $6.95          |
| 1,000             | 6,952,000    | $69.50         |

## Understanding the Example

### Source Files

**Python** — a mock authentication system: `auth.py` (imports `config.py`),
`config.py`, `user.py`, `database.py` (both unrelated to `auth.py`).

**Go** (`go.mod` module `glmdemo`) — `service/handler.go` imports the package
`service/util` (`service/util/helper.go`).

**JavaScript/TypeScript** — `web/app.js` and `web/format.ts` both
`require`/`import` `web/utils.js`.

There is no `test_auth.py` or `logger.py` in this repo, despite what an
earlier version of this README claimed — every number here is reproducible by
running the scripts yourself.

### Blast Radius Results

| Changed | Radius | Reduction |
|---|---|---|
| `auth.py` | `auth.py`, `config.py` | 53.8% (of 9 files) |
| `service/util/helper.go` | + `service/handler.go` | 95.7% |
| `web/utils.js` | + `web/app.js`, `web/format.ts` | 93.5% |

Reduction rises with the number of files *not* pulled into the radius — it's a
property of the repo's size and shape, not a fixed constant. Reproduce these
with `python token_benchmark.py <file>`.

## Why This Matters

### For Developers
- Faster code reviews
- Less context switching
- Focused on relevant changes

### For Teams
- Reduced review time
- Lower API costs
- More efficient CI/CD

### For Organizations
- Significant cost savings on frequent reviews
- Better code quality through focused reviews
- Scalable code review process

## Extending the System

`blast_radius.py` implements the engine (AST/tree-sitter parsing, the reverse
dependency graph, PageRank, incremental caching) and ships Python, JS/TS and Go
support. What's still a genuine extension, not a demo:

1. **Integrate with GLM-4:** stream `select()`'s file list straight into a
   review prompt; optimize for GLM-4's context window; add prompt caching for
   files that recur across reviews.
2. **CI/CD integration:** a git pre-push hook or PR check that runs
   `count_bytes.py` against the diff's changed files and posts the radius as a
   PR comment.
3. **More languages:** add an entry to `EXT_LANGUAGE`, a raw-import extractor,
   and a resolver in `blast_radius.py` — Java and Rust are the natural next
   ones (Java needs a source-root heuristic; Rust's `mod`/`use` resolution is
   closer to Go's).

## Contributing

- [ ] CI/CD integration example (git hook or GitHub Action)
- [ ] Java / Rust language support
- [ ] Benchmark on a real (non-demo) repository
- [ ] Symbol-level nodes (function/class, not whole file)

## License

MIT License - feel free to use this as a reference for building your own token-optimized code review system.

## Author

Created as a demonstration of GLM Code Graph architecture benefits.

## Related Resources

- [GLM-4 API Documentation](https://open.bigmodel.cn/)
- [Tree-sitter Documentation](https://tree-sitter.github.io/tree-sitter/)
- [Token Usage Optimization Best Practices](https://platform.openai.com/docs/guides/tokens)

---

**Need help?** Open an issue on GitHub for questions or suggestions.
