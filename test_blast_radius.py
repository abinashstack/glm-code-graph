#!/usr/bin/env python3
"""Verification for blast_radius.select -- run: python test_blast_radius.py"""

import shutil
import tempfile
from pathlib import Path

from blast_radius import build_graph, select

ROOT = Path(__file__).parent


def test_ast_finds_function_local_import():
    # auth.py has `from config import SECRET_KEY` *inside* a method. A line-prefix
    # scan of the module's leading lines would miss it; the AST does not.
    graph = build_graph(ROOT)
    assert "config" in graph.modules["auth"].imports


def test_change_to_config_pulls_its_importer():
    sel = select(ROOT, ["config.py"])
    assert "auth.py" in sel.files
    assert sel.reason["auth.py"].startswith("imports the change")


def test_unrelated_change_stays_narrow():
    # nothing imports user.py or database.py, so their radius is just themselves.
    for changed in ("user.py", "database.py"):
        sel = select(ROOT, [changed])
        assert sel.files == [changed], (changed, sel.files)


def test_forward_dependency_is_context_not_impact():
    sel = select(ROOT, ["auth.py"])
    assert sel.reason["auth.py"] == "changed"
    assert sel.reason["config.py"] == "dependency of the change"


def test_token_budget_trims_but_keeps_changed_file():
    sel = select(ROOT, ["config.py"], token_budget=1)
    assert sel.files == ["config.py"]
    assert "auth.py" in sel.dropped


def test_reduction_is_reported():
    sel = select(ROOT, ["user.py"])
    assert 0 < sel.token_reduction < 100


def test_budget_trim_is_a_priority_prefix():
    # x changed; a imports x (1 hop up, large); b imports a (2 hops up, small).
    # A budget that fits b but not a must still drop b -- keeping it would leave
    # the selection missing a higher-priority file (a) than one it kept (b).
    work = Path(tempfile.mkdtemp())
    try:
        (work / "x.py").write_text("VALUE = 1\n")
        (work / "a.py").write_text("import x\n" + "# pad\n" * 200)
        (work / "b.py").write_text("import a\n")
        sel = select(work, ["x.py"], token_budget=12)
        assert sel.files == ["x.py"], sel.files
        assert set(sel.dropped) == {"a.py", "b.py"}, sel.dropped
    finally:
        shutil.rmtree(work)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL {t.__name__}: {exc}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    raise SystemExit(1 if failed else 0)
