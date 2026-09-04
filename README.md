# GLM Code Graph - Token Reduction Demonstration

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

Imports are read from the **AST**, so aliased imports, `from x import *`, and
function-local imports are all detected — a line-prefix string scan misses them.

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
- Python 3.8+ (for the verification scripts)

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
├── blast_radius.py             # The analysis: graph build + reverse closure + trim
├── test_blast_radius.py        # Verification (python test_blast_radius.py)
├── count_bytes.py              # CLI: reduction for a change
├── token_reduction_manual.py   # CLI: verbose, shows the graph
├── token_benchmark.py          # CLI: side-by-side token comparison (needs tiktoken)
├── auth.py                     # Mock code under review: auth + tokens (imports config)
├── config.py                   # Mock: configuration
├── user.py                     # Mock: user service
└── database.py                 # Mock: database layer
```

The `.ps1`, `.bat`, `.sh`, `.cs` and `.js` files are older single-file ports of
the byte-count estimate and are not wired to `blast_radius.py`.

## How It Works

`blast_radius.build_graph()` parses every `*.py` file with the `ast` module,
recording each module's first-party imports and top-level symbols. Edges are
`A imports B`; the reverse index gives `B is imported by A`.

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

The repository contains a mock authentication system:

**auth.py** (2,436 bytes)
- Handles authentication and token management
- Imports `logger` module

**user.py** (1,809 bytes)
- User management functions
- Unrelated to auth changes

**database.py** (2,527 bytes)
- Database operations
- No imports from auth module

**config.py** (1,724 bytes)
- Configuration settings
- No imports from auth module

**test_auth.py** (2,899 bytes)
- Tests for auth module
- Should be reviewed (detected by pattern matching)

### Blast Radius Results

When reviewing `auth.py`:
- **Includes**: `auth.py`, `logger.py` (and test files)
- **Excludes**: `user.py`, `database.py`, `config.py`
- **Result**: 6 files saved (75% reduction)

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

This repository demonstrates the concept. To build a production-ready version:

1. **Implement the blast radius engine:**
   - Use Tree-sitter for parsing
   - Build dependency graph (call graphs, import graphs)
   - Calculate blast radius with configurable depth

2. **Integrate with GLM-4:**
   - Use streaming API
   - Optimize context window (128k-256k tokens)
   - Implement prompt caching

3. **Add CI/CD integration:**
   - Git hooks for automated reviews
   - Pull request checks
   - PR comment automation

4. **Multi-language support:**
   - Extend to JavaScript, TypeScript, Go, etc.
   - Update parsers for each language

## Contributing

Contributions are welcome! Areas for improvement:

- [ ] Add more example codebases
- [ ] Implement actual blast radius engine
- [ ] Create CI/CD integration examples
- [ ] Add support for more languages
- [ ] Benchmark performance
- [ ] Write unit tests

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
