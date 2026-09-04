#!/usr/bin/env python3
"""
Token reduction check for a code review.

Thin wrapper over ``blast_radius.select`` -- computes the reverse dependency
closure of a change and reports the token saving versus reading the whole repo.

    python count_bytes.py                 # review auth.py
    python count_bytes.py user.py config.py
    python count_bytes.py auth.py --budget=1500
"""

import sys
from pathlib import Path

from blast_radius import TOOLING, format_report, select


def main() -> None:
    changed = [a for a in sys.argv[1:] if not a.startswith("-")] or ["auth.py"]
    budget = next(
        (int(a.split("=", 1)[1]) for a in sys.argv[1:] if a.startswith("--budget=")),
        None,
    )
    result = select(Path(__file__).parent, changed, token_budget=budget, exclude=TOOLING)
    print(format_report(result))

    saved = result.full_tokens - result.tokens
    print(f"\n  saved ~{saved:,} tokens/review  (~${saved * 1e-5:.2f} at $0.00001/token)")


if __name__ == "__main__":
    main()
