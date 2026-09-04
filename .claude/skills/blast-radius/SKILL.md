---
name: blast-radius
description: Given one or more changed files (Python, JavaScript, TypeScript, or Go), compute and print the minimal set of files a reviewer needs to read -- the reverse dependency closure, parsed with ast/tree-sitter, optionally trimmed to a token budget. Use when the user says "review this change", "what breaks if I change X", "blast radius of <file>", or wants a token-efficient review instead of reading the whole repo.
metadata:
  author: abinashstack
  version: "1.0.0"
  source: https://github.com/abinashstack/glm-code-graph
  compatible_with: ["Claude Code", "zai-org/GLM-skills ecosystem (OpenCode, OpenClaw, AutoClaw)"]
---

# Blast Radius

Computes the files a code reviewer actually needs to read for a change, instead
of the whole repo. Backed by `blast_radius.py` in this repository. Python needs
no dependency (stdlib `ast`); JavaScript, TypeScript and Go need
`pip install -r requirements-languages.txt` (tree-sitter grammars) -- without
it, files in those languages are skipped as isolated nodes rather than
crashing. `tiktoken` gives exact token counts when installed, otherwise a
`bytes / 4` estimate. The graph is cached by content hash in
`.blast_radius_cache.json`, so re-running after a small change only re-parses
what changed.

## When to use this skill

- The user names one or more changed files and asks what else needs review,
  what could break, or wants "the blast radius."
- The user wants a token-efficient review of a change instead of reading every
  file in the repo.
- Not for: diagnosing *why* code is broken (use tests/a debugger for that), or
  for languages without a shipped resolver (Java, Rust, C/C++, ... -- see
  README's "Extending the System" for how to add one).

## How to run it

```bash
python blast_radius.py <changed_file> [<changed_file2> ...] [--budget=N] [--depth=N]
```

- No flags: depth 3, no token budget (nothing gets trimmed).
- `--budget=N`: cap the total token count. Lowest-priority files are dropped
  first as a priority-prefix cut; changed files are never dropped.
- `--depth=N`: how many reverse-import hops to follow (default 3).

Run it from the repository root.

## Reading the output

```
================================================================
  BLAST RADIUS  (auth.py)
================================================================

  read 2 file(s), skip 2:

    auth.py    changed
    config.py  dependency of the change

----------------------------------------------------------------
  tokens        890   (full review: 1,719)
  reduction   48.2%
================================================================
```

- **`changed`** -- the file(s) actually being modified.
- **`imports the change (N hops up)`** -- this file imports the changed one,
  directly or transitively, and may break. The primary review target list.
- **`dependency of the change`** -- one hop of context: what the change itself
  relies on, to understand it.
- **`test over impacted code`** -- a test covering something in the impact set;
  read/run it.

Open exactly these files for the review. If one of them references something
unclear, re-run with a larger `--depth` rather than reading the rest of the
repo ad hoc.

## As a library (no subprocess)

```python
from blast_radius import select, format_report

sel = select(repo_root, ["auth.py"], max_depth=3, token_budget=8000)
print(format_report(sel))
sel.files      # ordered list of repo-relative paths to read
sel.reason     # {path: why it's included}
sel.dropped    # files cut to fit the budget
```

## Failure modes

| Symptom | Fix |
| --- | --- |
| `ValueError: not a module in <root>` | The changed path isn't a `.py` file under `root`. Pass the correct path. |
| Radius looks too narrow (misses an obvious caller) | Increase `--depth` -- the walk stops at the given hop count by design. |
| Radius looks too wide | A widely-imported module (config, constants) was changed -- that's real fan-out, not a bug. Use `--budget=N` and read the highest-priority files first. |
| No `tiktoken` installed | Falls back to a `bytes / 4` estimate automatically -- counts are approximate, not wrong. |

## Portability

This skill wraps a plain, dependency-light Python module -- nothing here is
model-specific. The `SKILL.md` format is shared with
[zai-org/GLM-skills](https://github.com/zai-org/GLM-skills), so this file works
unchanged whether the driving model is Claude or a GLM model, in any harness
that reads `SKILL.md` (Claude Code, OpenCode, OpenClaw, AutoClaw).
